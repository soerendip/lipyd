#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#  This file is part of the `emese` python module
#
#  Copyright (c) 2015-2017 - EMBL
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

import bs4
import re
import warnings
import imp
import copy
from collections import defaultdict

import emese._curl as _curl

urlMasses = 'http://www.ciaaw.org/atomic-masses.htm'
urlWeights = 'http://www.ciaaw.org/atomic-weights.htm'
urlAbundances = 'http://www.ciaaw.org/isotopic-abundances.htm'
reNonDigit = re.compile(r'[^\d.]+')

proton = 1.00727646677
electron = 0.00054857990924
neutron = 1.00866491588

# ##
def getMasses(url):
    
    """
    Downloads an HTML table from CIAAW webpage
    and extracts the atomic mass or weight information.
    """
    
    c = _curl.Curl(url, silent = False)
    reqMasses = c.result
    with warnings.catch_warnings():
        # there is a deprecated call in lxml
        warnings.simplefilter('ignore', DeprecationWarning)
        soupMasses = bs4.BeautifulSoup(reqMasses, 'lxml')

    mass = {}
    symbol = None
    a = None

    for tr in soupMasses.find_all('tr'):
        tr = [td for td in tr.find_all('td')]
        if len(tr) == 5:
            symbol = tr[1].text.strip()
            massdb[symbol] = {}
        try:
            a = int(tr[-2].text.strip())
            m = [float(reNonDigit.sub('', i)) for i in tr[-1].text.split(',')]
            m = sum(m) / len(m)
            massdb[symbol][a] = m
        except (ValueError, IndexError):
            continue
    mass['proton']   = 1.00727646677
    mass['electron'] = 0.00054857990924
    mass['neutron']  = 1.00866491588
    return mass

def getMassMonoIso():
    """
    Obtains monoisotopic masses from CIAAW webpage.
    Stores the result in `massMonoIso` module level variable.
    """
    globals()['massMonoIso'] = getMasses(urlMasses)

def getMassFirstIso():
    """
    Obtains the
    """
    
    if 'massMonoIso' not in globals():
        getMassMonoIso()
    if 'freqIso' not in globals():
        getFreqIso()
    firstIso = {}
    for symbol, isos in iteritems(massMonoIso):
        if symbol in freqIso:
            try:
                firstIso[symbol] = \
                    isos[max(freqIso[symbol].items(), key = lambda i: i[1])[0]]
            except:
                continue
    firstIso['proton']   = proton
    firstIso['electron'] = electron
    firstIso['neutron']  = neutron
    globals()['massFirstIso'] = firstIso

def getWeightStd():
    """
    Obtains atomic waights from CIAAW webpage.
    Stores the result in `weightStd` module level variable.
    """
    globals()['weightStd'] = getMasses(urlWeights)

def getFreqIso():
    """
    Obtains isotope abundances from CIAAW webpage.
    Stores the result in `freqIso` module level variable.
    """
    c = _curl.Curl(urlAbundances, silent = False)
    reqAbundances = c.result.split('\n')
    
    # fixing erroneous HTML from CIAAW:
    for i, l in enumerate(reqAbundances[:-1]):
        
        l = l.strip()
        # print('..%s.. ..%s..' % (l[-5:], reqAbundances[i + 1][:3]))
        if l[-5:] == '</tr>' and reqAbundances[i + 1][:3] == '<td':
            # print('ermfeoirm')
            reqAbundances[i + 1] = '<tr>%s' % reqAbundances[i + 1]
    
    with warnings.catch_warnings():
        # there is a deprecated call in lxml
        warnings.simplefilter('ignore', DeprecationWarning)
        soupAbundances = bs4.BeautifulSoup('\n'.join(reqAbundances), 'lxml')
    
    freqIso = {}
    symbol = None
    a = None
    
    for tr in soupAbundances.find_all('tr'):
        tr = [td for td in tr.find_all('td')]
        if len(tr) == 6:
            symbol = tr[1].text.strip()
            freqIso[symbol] = {}
        ai = -3 if len(tr) == 6 else -2
        try:
            a = int(tr[ai].text.strip())
            p = [float(reNonDigit.sub('', i)) for i in tr[ai + 1].text.split(',')]
            p = sum(p) / len(p)
            freqIso[symbol][a] = p
        except (ValueError, IndexError, KeyError):
            continue
    globals()['freqIso'] = freqIso

massdb = {
    "proton": 1.00727646677,
    "electron": 0.00054857990924,
    "neutron": 1.00866491588,
    "H":  1.007825,
    "He": 4.002602,
    "Li": 6.941,
    "Be": 9.012182,
    "B":  10.811,
    "C":  12.0107,
    "N":  14.00674,
    "O":  15.9994,
    "F":  18.9984032,
    "Ne": 20.1797,
    "Na": 22.989768,
    "Mg": 24.3050,
    "Al": 26.981539,
    "Si": 28.0855,
    "P":  30.973762,
    "S":  32.066,
    "Cl": 35.4527,
    "Ar": 39.948,
    "K":  39.0983,
    "Ca": 40.078,
    "Sc": 44.955910,
    "Ti": 47.88,
    "V":  50.9415,
    "Cr": 51.9961,
    "Mn": 54.93805,
    "Fe": 55.847,
    "Co": 58.93320,
    "Ni": 58.6934,
    "Cu": 63.546,
    "Zn": 65.39,
    "Ga": 69.723,
    "Ge": 72.61,
    "As": 74.92159,
    "Se": 78.96,
    "Br": 79.904,
    "Kr": 83.80,
    "Rb": 85.4678,
    "Sr": 87.62,
    "Y":  88.90585,
    "Zr": 91.224,
    "Nb": 92.90638,
    "Mo": 95.94,
    "Tc": 98.0,
    "Ru": 101.07,
    "Rh": 102.90550,
    "Pd": 106.42,
    "Ag": 107.8682,
    "Cd": 112.411,
    "In": 114.82,
    "Sn": 118.710,
    "Sb": 121.757,
    "Te": 127.60,
    "I":  126.90447,
    "Xe": 131.29,
    "Cs": 132.90543,
    "Ba": 137.327,
    "La": 138.9055,
    "Ce": 140.115,
    "Pr": 140.90765,
    "Nd": 144.24,
    "Pm": 145.0,
    "Sm": 150.36,
    "Eu": 151.965,
    "Gd": 157.25,
    "Tb": 158.92534,
    "Dy": 162.50,
    "Ho": 164.93032,
    "Er": 167.26,
    "Tm": 168.93421,
    "Yb": 173.04,
    "Lu": 174.967,
    "Hf": 178.49,
    "Ta": 180.9479,
    "W":  183.85,
    "Re": 186.207,
    "Os": 190.2,
    "Ir": 192.22,
    "Pt": 195.08,
    "Au": 196.96654,
    "Hg": 200.59,
    "Tl": 204.3833,
    "Pb": 207.2,
    "Bi": 208.98037,
    "Po": 209,
    "At": 210,
    "Rn": 222,
    "Fr": 223,
    "Ra": 226.0254,
    "Ac": 227,
    "Th": 232.0381,
    "Pa": 213.0359,
    "U":  238.0289,
    "Np": 237.0482,
    "Pu": 244,
    "Am": 243,
    "Cm": 247,
    "Bk": 247,
    "Cf": 251,
    "Es": 252,
    "Fm": 257,
    "Md": 258,
    "No": 259,
    "Lr": 260,
    "Rf": 261,
    "Db": 262,
    "Sg": 263,
    "Bh": 262,
    "Hs": 265,
    "Mt": 266,
}

isotopes = {
    "H2": 2.01410178,
    "H3": 3.0160492,
    "C13": 13.003355,
    "N15": 15.000109,
    "O17": 16.999132,
    "O18": 17.999160,
    "S33": 32.971458,
    "S34": 33.967867,
    "S35": 35.967081
}

iso_freq = {
    "H2": 0.000115,
    "H3": 0.0,
    "C13": 0.0107,
    "N15": 0.0068,
    "O17": 0.00038,
    "O18": 0.00205,
    "S33": 0.0076,
    "S34": 0.0429,
    "S35": 0.0002
}

fragments = {
    'neg': {
        'PI [InsP-H2O]-': 'C6H12O9P',
        'PI [InsP-H]-': 'C6H12O9P',
        'PI [InsP-2H2O]-': 'C6H12O9P',
        'PI headgroup [G-P-I]': 'C9H14O9P',
        'PG/PA/PS/PI partial headgroup': 'C3H6O5P',
        'Cer1P/PIP phosphate': 'H2O4P',
        'SM CH3+COOH': 'CH3COOH',
        'Cer1P/PIP/PL metaphosphate': 'O3P',
        'PE headgroup [P-E]': 'C2H7O4NP',
        'PE headgroup [G-P-E]': 'C5H11O5PN',
        'PG headgroup [G-P]': 'C3H8O6P',
        'PS headgroup NL': 'C3H5O2N'
    },
    'pos': {
        'PC headgroup [P-C]': 'C5H15O4NP',
        'PC/SM choline [C]': 'C5H12N',
        'PC/SM choline [N(CH3)2CH2]': 'C3H8N',
        'PC/SM choline [C+H2O]': 'C5H14ON',
        'PC/SM choline [Et+P]': 'C2H6O4P',
        'PC/SM choline [NH(CH3)3]': 'C3H10N',
        'Cer sphingosine(d18:1)-carbon-2xH2O': 'C17H34N',
        'Cer sphingosine(d18:1)-2xH2O': 'C18H34N',
        'Cer/SM sphingosine(d18:1)-H2O': 'C18H36ON',
        'PI headgroup NL': 'C6H12O9P',
        'PC/SM headgroup NL': 'C5H14NO4P',
        'Cer sphingosine(d18:1)-2xH2O': 'C18H34N'
    }
}

class Mass(object):
    """
    
    Thanks for
    https://github.com/bsimas/molecular-weight/blob/master/chemweight.py
    
    """
    
    def __init__(self, formula = None, mass = None, charge = 0, isotope = 0, **kwargs):
        """
        This class is very similar to `Formula`. Actually it can have 
        
        **kwargs: elements & counts, e.g. c = 6, h = 12, o = 6...
        """
        if 'massFirstIso' not in globals():
            getMassFirstIso()
        self.exmass = massFirstIso
        self.charge = charge
        self.isotope = isotope
        self.reform = re.compile(r'([A-Za-z][a-z]*)([0-9]*)')
        if formula is None:
            formula = ''.join('%s%u'%(elem.capitalize(), num) \
                for elem, num in iteritems(kwargs))
        self.formula = formula
        self.calc_weight()
    
    def __neg__(self):
        return -1 * self.weight
    
    def __add__(self, other):
        return float(other) + self.weight
    
    def __radd__(self, other):
        return self.__add__(other)
    
    def __iadd__(self, other):
        self.weight += float(other)
    
    def __sub__(self, other):
        return self.weight - float(other)
    
    def __rsub__(self, other):
        return float(other) - self.weight
    
    def __isub__(self, other):
        self.weight += float(other)
    
    def __truediv__(self, other):
        return self.weight / float(other)
    
    def __rtruediv__(self, other):
        return float(other) / self.weight
    
    def __itruediv__(self, other):
        self.weight /= float(other)
    
    def __mul__(self, other):
        return self.weight * float(other)
    
    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __imul__(self, other):
        self.weight *= float(other)
    
    def __float__(self):
        return self.weight
    
    def __eq__(self, other):
        return abs(self.weight - float(other)) <= 0.01
    
    def calc_weight(self):
        
        atoms = (
            self.reform.findall(self.formula)
            if not hasattr(self, 'atoms')
            else self.atoms.items()
        )
        w = 0.0
        for element, count in atoms:
            count = int(count or '1')
            w += self.exmass[element] * count
        w -= self.charge * massdb['electron']
        w += self.isotope * massdb['neutron']
        self.weight = w
        
        self.weight_calculated = self.has_weight()
    
    def has_weight(self):
        
        return self.weight > 0.0
    
    def has_formula(self):
        
        return bool(self.formula)
    
    def reload(self):
        modname = self.__class__.__module__
        mod = __import__(modname, fromlist=[modname.split('.')[0]])
        imp.reload(mod)
        new = getattr(mod, self.__class__.__name__)
        setattr(self, '__class__', new)


class Formula(Mass):
    
    def __init__(self, formula = None, charge = 0, isotope = 0, **kwargs):
        
        if isinstance(formula, Formula):
            
            charge = formula.charge
            isotope = formula.isotope
            formula = formula.formula
        
        MolWeight.__init__(self, formula, charge, isotope, **kwargs)
        
        self.atoms = defaultdict(lambda: 0)
        self.add(self.formula)
    
    def __add__(self, other):
        
        return Formula('%s%s' % (self.formula,
            other.formula if hasattr(other, 'formula') else other),
            self.charge + (other.charge if hasattr(other, 'charge') else 0),
            self.isotope + (other.isotope if hasattr(other, 'isotope') else 0)
        )
    
    def __iadd__(self, other):
        
        self.charge += (other.charge if hasattr(other, 'charge') else 0)
        self.isotope += (other.isotope if hasattr(other, 'isotope') else 0)
        self.add(other.formula if hasattr(other, 'formula') else other)
        
        return self
    
    def __sub__(self, other):
        
        new = copy.copy(self)
        new.__isub__(other)
        return new
    
    def __isub__(self, other):
        
        self.charge -= (other.charge if hasattr(other, 'charge') else 0)
        self.isotope -= (other.isotope if hasattr(other, 'isotope') else 0)
        self.sub(other.formula if hasattr(other, 'formula') else other)
        
        return self
    
    def as_weight(self):
        
        return MolWeight(self.formula, self.charge, self.isotope)
    
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
        self.calc_weight()
    
    def bind(self, other, loss = 'H2O'):
        
        return self + other - loss
    
    def split(self, product1, add = 'H2O'):
        
        product1 = Formula(product1)
        
        return product1, self - product1 + add
