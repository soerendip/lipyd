#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#  This file is part of the `lipyd` python module
#
#  Copyright (c) 2015-2019 - EMBL
#
#  File author(s):
#  Dénes Türei (turei.denes@gmail.com)
#  Igor Bulanov
#
#  Distributed under the GNU GPLv3 License.
#  See accompanying file LICENSE.txt or copy at
#      http://www.gnu.org/licenses/gpl-3.0.html
#
#  Website: http://denes.omnipathdb.org/
#

import imp
import sys
import re

try:
    import openbabel.pybel as pybel
    if 'ipykernel' not in sys.modules and pybel.tk is None:
        try:
            import tkinter
            import PIL
            import PIL.ImageTk
            pybel.tk = tkinter
            pybel.PIL = PIL.Image
            pybel.piltk = PIL.ImageTk
        except:
            sys.stdout.write(
                ':: `PIL` or `tkinter` not available.\n'
                '   `pybel` won\'t be able to draw molecules.\n'
            )
except:
    sys.stdout.write(':: Module `pybel` not available.\n')

resyn = re.compile(
    r'(^[A-Z]{2,})\(([0-9]+:[0-9]+)\(.*\)/([0-9]+:[0-9]+)\(.*\)\)'
)
rehg  = re.compile(r'^([A-Z]{2,4})(\(.*\))')
refa  = re.compile(r'C([0-9]+:[0-9]+)n?-?[-0-9]*$')
refa2 = re.compile(r'([0-9]{1,2}:[0-9])\(?[0-9EZ]*\)?$')
hgsyn = {
    'TG': 'TAG',
    'DG': 'DAG'
}

class SdfReader(object):
    """ """
    
    names_default = {
        'PUBCHEM_CID': 'pubchem',
        'CHEBI_ID': 'chebi',
        'SYNONYMS': 'synonym',
        'INCHI': 'inchi',
        'INCHIKEY': 'inchikey',
        'COMMON_NAME': 'commname',
        'SYSTEMATIC_NAME': 'sysname'
    }
    
    annots_default = {'EXACT_MASS', 'FORMULA'}
    
    def __init__(self, fp, names = None, annots = None, silent = False):
        """
        Processes and serves data from an sdf file.
        
        Builds an index of the file and retrieve the records on demand.
        Note, sdf is not a well defined or well kept standard, this reader
        has been developed to process the LipidMaps database. Once there
        is a need to use with other databases we are happy to adapt to
        their formats.
        
        Args
        ----
        :param file fp:
            An open file pointer to the SDF file.
        :param dict names:
            These are the names to build indexes for. Once indexing is done
            it's possible to search and retrieve records by these IDs and
            names. By deafult the names in `names_default` are used. Names
            provided here are added to the defaults. Keys of the dict are
            labels as used in the sdf, values of the dict are the attribute
            names of the indexes.
        :param set annots:
            Additional annotations to be read. These are the data to be
            retrieved with each record. Works the same way as `names`.
        :param bool silent:
            Print number of records at the end of indexing.
        """
        
        self.fp = fp
        self.name = self.fp.name
        self.data = {}
        self.mainkey  = {}
        self.indexed = False
        self.silent = silent
        
        self.names = names or {}
        self.names.update(self.names_default)
        self.annots = annots or set()
        self.annots.update(self.annots_default)
        
        for name in self.names.values():
            
            setattr(self, name, {})
        
        self._byte_mode()
        self._file_size()
        self.index()
    
    def reload(self):
        """ """
        
        modname = self.__class__.__module__
        mod = __import__(modname, fromlist=[modname.split('.')[0]])
        imp.reload(mod)
        new = getattr(mod, self.__class__.__name__)
        setattr(self, '__class__', new)
    
    def _byte_mode(self):
        """ """
        
        if hasattr(self.fp, 'mode'):
            
            if 'b' not in self.fp.mode:
                
                self.fp.close()
                self.fp = open(self.name, 'rb')
    
    def _file_size(self):
        """ """
        
        self.fp.seek(-1, 2)
        self.eof = self.fp.tell()
    
    def read(self,
            index_only = True,
            one_record = False,
            go_to = 0
        ):
        """Performs all reading operations on the sdf file.
        
        This method is able to read the entire file, scan the file and build
        an index of records, and retrieve one record.
        
        Args
        ----

        Parameters
        ----------
        bool :
            index_only:
            Do not read the file but only build an index.
        bool :
            one_record:
            Read only one record.
        int :
            go_to:
            Go to this byte offset in the file and start reading there.
        index_only :
             (Default value = True)
        one_record :
             (Default value = False)
        go_to :
             (Default value = 0)

        Returns
        -------

        """
        
        self.fp.seek(go_to)
        
        expect_new = True
        molpart = None
        namepart = False
        name_or_id = False
        _id = None
        mol = ''
        this_offset = None
        offset = 0
        name  = {}
        annot = {}
        namekey = None
        
        for l in self.fp:
            
            llen = len(l)
            l = l.decode('utf-8')
            sl = l.strip()
            
            if not molpart:
                
                if name_or_id and len(sl) and sl[0] != '>' and sl[0] != '$':
                    expect_new = True
                
                if namekey and namekey in self.names:
                    name[namekey] = sl
                    namekey = None
                
                if namekey and namekey in self.annots:
                    annot[namekey] = sl
                    namekey = None
                
                if sl[:3] == '> <':
                    name_or_id = False
                    namepart = True
                    namekey  = sl[3:-1]
                
                if namepart and sl == '':
                    name_or_id = True
                
                if expect_new and len(l):
                    
                    _id = sl
                    name = {}
                    annot = {}
                    this_offset = offset
                    expect_new = False
                    molpart = 1
                    comment = ''
            
            elif molpart == 1:
                
                source = sl
                molpart += 1
            
            elif molpart == 2 and len(sl):
                
                if not sl[0].isdigit():
                    
                    comment = '%s %s' % (comment, sl)
                    
                else:
                    
                    molpart = 3
            
            if sl == '$$$$':
                expect_new = True
            
            if molpart == 3:
                
                if not index_only:
                    
                    mol = '%s%s' % (mol, l)
                
                if sl == 'M  END':
                    molpart = None
                    namepart = True
                    name_or_id = True
            
            if expect_new or self.fp.tell() == self.eof:
                
                if one_record:
                    
                    return {
                        'id': _id,
                        'source': source,
                        'comment': comment,
                        'mol': mol,
                        'name': name,
                        'annot': annot
                    }
                
                # this is indexing: we build dicts of names
                self.mainkey[_id] = this_offset
                
                if 'COMMON_NAME' in name:
                    
                    m = refa2.match(name['COMMON_NAME'])
                    
                    if m:
                        
                        if 'SYNONYMS' not in name:
                            
                            name['SYNONYMS'] = 'FA(%s)' % m.groups()[0]
                            
                        else:
                            
                            name['SYNONYMS'] = '%s;FA(%s)' % (
                                name['SYNONYMS'],
                                m.groups()[0]
                            )
                
                for k, v in self.names.items():
                    
                    if k in name:
                        
                        if k == 'SYNONYMS':
                            
                            syns = set(
                                syn.strip() for syn in name[k].split(';')
                            )
                            
                            syns2 = set([])
                            
                            for syn in syns:
                                
                                m = rehg.match(syn)
                                
                                if m:
                                    
                                    m = m.groups()
                                    
                                    if m[0] in hgsyn:
                                        
                                        syns2.add(
                                            '%s%s' % (hgsyn[m[0]], m[1])
                                        )
                            
                            syns.update(syns2)
                            syn2 = set([])
                            
                            for syn in syns:
                                
                                m = resyn.match(syn)
                                
                                if m:
                                    
                                    syns2.add('%s(%s/%s)' % m.groups())
                                
                                m = refa.match(syn)
                                
                                if m:
                                    
                                    syns2.add('FA(%s)' % m.groups()[0])
                            
                            syns.update(syns2)
                            
                            for syn in syns:
                                
                                if syn not in self.synonym:
                                    self.synonym[syn] = set([])
                                
                                self.synonym[syn].add(this_offset)
                            
                        else:
                            
                            getattr(self, v)[name[k]] = this_offset
                
                if not index_only:
                    
                    self.data[this_offset] = {
                        'id': _id,
                        'source': source,
                        'comment': comment,
                        'mol': mol,
                        'name': name,
                        'annot': annot
                    }
            
            offset += llen
        
        if index_only:
            
            self.indexed = True
    
    def index(self):
        """ """
        
        self.read(index_only = True)
        self.index_info()
    
    def get_record(self, name, typ):
        """Retrieves all records matching `name`.
        
        Returns list of records or empty list if none found.
        Each record is a dict of processed values from the sdf file.
        
        Args
        ----

        Parameters
        ----------
        str :
            name:
            Molecule name or identifier.
        str :
            typ:
            Type of name or identifier. These are the attribute names of the
            index dicts which are taken from the values in the `names`
            dict.
        name :
            
        typ :
            

        Returns
        -------

        """
        
        result = []
        
        if hasattr(self, typ):
            
            index = getattr(self, typ)
            
            if name in index:
                
                if typ == 'synonym':
                    
                    for offset in index[name]:
                        
                        result.append(
                            self.read(
                                index_only = False,
                                one_record = True,
                                go_to = offset
                            )
                        )
                    
                else:
                    
                    offset = index[name]
                    result.append(
                        self.read(
                            index_only = False,
                            one_record = True,
                            go_to = offset
                        )
                    )
        
        return result
    
    def get_obmol(self, name, typ, use_mol = False):
        """Returns generator yielding `pybel.Molecule` instances for `name`.
        
        Args
        ----

        Parameters
        ----------
        str :
            name:
            Molecule name or ID.
        str :
            typ:
            Type of the name or identifier.
        bool :
            use_mol:
            Process structures from mol format.
            By default structures are processed from InChI.
        name :
            
        typ :
            
        use_mol :
             (Default value = False)

        Returns
        -------

        """
        
        records = self.get_record(name, typ)
        
        for rec in records:
            
            if use_mol:
                
                mol = self.record_to_obmol_mol(rec)
                
            else:
                
                mol = self.record_to_obmol(rec)
            
            mol.db_id = rec['id']
            title = []
            if 'COMMON_NAME' in rec['name']:
                title.append(rec['name']['COMMON_NAME'])
            if 'SYNONYMS' in rec['name']:
                title.extend(rec['name']['SYNONYMS'].split(';'))
            if 'SYSTEMATIC_NAME' in rec['name']:
                title.append(rec['name']['SYSTEMATIC_NAME'])
            mol.title = '|'.join(n.strip() for n in title)
            mol.lipidmaps = rec['id']
            if 'INCHI' in rec['name']:
                mol.inchi = rec['name']['INCHI']
            if 'PUBCHEM_CID' in rec['name']:
                mol.pubchem = rec['name']['PUBCHEM_CID']
            if 'CHEBI_ID' in rec['name']:
                mol.chebi = rec['name']['CHEBI_ID']
            if 'COMMON_NAME' in rec['name']:
                mol.name = rec['name']['COMMON_NAME']
            
            yield mol
    
    def record_to_obmol(self, record):
        """Processes a record to `pybel.Molecule` object.

        Parameters
        ----------
        record :
            

        Returns
        -------

        """
        
        if 'INCHI' in record['name']:
            
            return pybel.readstring('inchi', record['name']['INCHI'])
            
        else:
            
            sys.stdout.write(
                'No InChI for `%s`!\n' % record['name']['COMMON_NAME']
            )
    
    def record_to_obmol_mol(self, record):
        """

        Parameters
        ----------
        record :
            

        Returns
        -------

        """
        
        return pybel.readstring('mol', self.get_mol(record))
    
    @staticmethod
    def get_mol(record):
        """Returns structure as a string in mol format.

        Parameters
        ----------
        record :
            

        Returns
        -------

        """
        
        return '%s\n  %s\n%s\n%s' % (
            record['id'],
            record['source'],
            record['comment'],
            record['mol']
        )
    
    def write_mol(self, name, typ, outf = None, return_data = False):
        """Writes a record into file in mol format.

        Parameters
        ----------
        name :
            
        typ :
            
        outf :
             (Default value = None)
        return_data :
             (Default value = False)

        Returns
        -------

        """
        
        outf = outf or '%s_%s_%s.mol'
        
        rr = self.get_record(name, typ)
        
        if not rr:
            
            return None
        
        if type(rr) is not list:
            
            rr = [rr]
        
        for r in rr:
            
            _outf = outf % (
                name.replace('/', '.'),
                r['name']['COMMON_NAME'].replace('/', '.').replace(' ', '..')
                    if 'COMMON_NAME' in r['name']
                    else '',
                r['id']
            )
            
            r['molfile'] = _outf
            
            with open(_outf, 'w') as fp:
                
                _ = fp.write(
                    self.get_mol(r)
                )
        
        if return_data:
            
            return rr
    
    def __iter__(self):
        
        return self.iter_records()
    
    def iter_records(self):
        """Iterates over all records in the sdf file."""
        
        for offset in self.mainkey.values():
            
            yield self.read(
                index_only = False,
                one_record = True,
                go_to = offset
            )
    
    def iter_obmol(self):
        """Iterates all structures in the file and yields `pybel.Molecule`
        objects.

        Parameters
        ----------

        Returns
        -------

        """
        
        for _id in self.mainkey.keys():
            
            for mol in self.get_obmol(_id, typ = 'mainkey'):
                
                yield mol
    
    def index_info(self):
        """Prints number of records indexed and name of the source file."""
        
        if not self.silent:
            
            sys.stdout.write('\t:: Indexed %u records from `%s`.\n' % (
                len(self.mainkey),
                self.name
            ))
    
    def __del__(self):
        
        self.fp.close()
