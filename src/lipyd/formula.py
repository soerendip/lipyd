# -*- coding: utf-8 -*-

#
#  This file is part of the `lipyd` python module
#
#  Copyright (c) 2015-2018 - EMBL
#
#  File author(s): Dénes Türei (turei.denes@gmail.com)
#
#  This code is not for public use.
#  Please do not redistribute.
#  For permission please contact me.
#
#  Website: http://www.ebi.ac.uk/~denes
#

from future.utils import iteritems

from collections import defaultdict

import lipyd.mass as mass
import lipyd.mz as mz


class Formula(mass.MassBase, mz.Mz):
    
    def __init__(
            self,
            formula = None,
            charge = 0,
            isotope = 0,
            z = 1,
            sign = None,
            tolerance = .01,
            **kwargs
        ):
        
        if isinstance(formula, Formula):
            
            charge = formula.charge
            isotope = formula.isotope
            formula = formula.formula
        
        mass.MassBase.__init__(self, formula, charge, isotope, **kwargs)
        
        self.reset_atoms()
        self.add(self.formula)
        
        mz.Mz.__init__(
            self,
            mz = self.mass / z,
            z = z,
            sign = sign,
            tolerance = tolerance
        )
    
    def __add__(self, other):
        
        if (
            not self.has_formula() or
            type(other) is float or
            (
                hasattr(other, 'has_formula') and
                not other.has_formula()
            )
        ):
            
            new_mass = MassBase.__add__(self, other)
            new_charge = self.charge + (
                other.charge
                if hasattr(other, 'charge')
                else 0
            )
            new_isotope = self.isotope + (
                other.isotope
                if hasattr(other, 'isotope')
                else 0
            )
            new = Formula(
                new_mass,
                charge = new_charge,
                isotope = new_isotope
            )
            
        else:
            
            new = Formula('%s%s' % (
                    self.formula,
                    other.formula
                        if hasattr(other, 'formula')
                        else other
                ),
                self.charge + (
                    other.charge
                    if hasattr(other, 'charge')
                    else 0
                ),
                self.isotope + (
                    other.isotope
                    if hasattr(other, 'isotope')
                    else 0
                )
            )
        
        new.update_mz(
            z = self.z,
            sign = self.sign,
            tolerance = self.tol
        )
        
        return new
    
    def __iadd__(self, other):
        
        if type(other) is float:
            
            self.mass = self.mass + other
            self.formula = ''
            self.reset_atoms()
            self.mass_calculated = False
            
        elif not self.has_formula():
            
            self.mass += other.mass
            
        else:
            
            self.add(other.formula if hasattr(other, 'formula') else other)
        
        self.charge += (other.charge if hasattr(other, 'charge') else 0)
        self.isotope += (other.isotope if hasattr(other, 'isotope') else 0)
        
        self.update_mz()
        
        return self
    
    def __sub__(self, other):
        
        new = copy.copy(self)
        new.__isub__(other)
        return new
    
    def __isub__(self, other):
        
        if type(other) is float:
            
            self.mass = self.mass - other
            self.formula = ''
            self.reset_atoms()
            self.mass_calculated = False
            
        elif not self.has_formula():
            
            self.mass -= other.mass
            
        else:
            
            self.sub(other.formula if hasattr(other, 'formula') else other)
        
        self.charge -= (other.charge if hasattr(other, 'charge') else 0)
        self.isotope -= (other.isotope if hasattr(other, 'isotope') else 0)
        
        return self
    
    def reset_atoms(self):
        
        self.atoms = defaultdict(lambda: 0)
    
    def as_mass(self):
        
        return MassBase(self.formula, self.charge, self.isotope)
    
    def add(self, formula):
        
        for elem, cnt in self.reform.findall(formula):
            self.atoms[elem] += int(cnt or '1')
        
        self.update()
    
    def sub(self, formula):
        
        for elem, cnt in self.reform.findall(formula):
            self.atoms[elem] -= int(cnt or '1')
            
            if self.atoms[elem] < 0:
                
                raise ValueError('Can not remove %s from %s: '
                    'too few %s atoms!' % (formula, self.formula, elem))
        
        self.update()
    
    def update(self):
        
        self.formula = ''.join('%s%u' % (elem, self.atoms[elem])
                                for elem in sorted(self.atoms.keys()))
        self.calc_mass()
    
    def bind(self, other, loss = 'H2O'):
        
        return self + other - loss
    
    def split(self, product1, add = 'H2O'):
        
        product1 = Formula(product1)
        
        return product1, self - product1 + add
    
    def update_mz(self, mz = None, z = 1, sign = None, tolerance = .01, overwrite = False):
        
        if not hasattr(self, 'z') or overwrite:
            self.z = z
        
        if not hasattr(self, 'sign') or overwrite:
            self.sign = sign
        
        if not hasattr(self, 'tolerance') or overwrite:
            self.tol = tolerance
        
        self.mz = mz or self.mass / self.z


class Mass(Formula):
    
    def __init__(self, formula_mass = None, charge = 0, isotope = 0, **kwargs):
        
        if ((formula_mass is None and not kwargs) and
            type(formula_mass) is float):
            
            # unknown formula, initializing an empty Formula:
            Formula.__init__(self, '', charge = charge, isotope = isotope)
            self.mass = formula_mass
            
        else:
            
            Formula.__init__(self, formula_mass,
                             charge = charge,
                             isotope = isotope,
                             **kwargs)
    
    def bind(self, other, loss = 'H2O'):
        
        if self.has_formula() and (type(other) is str):
            
            pass