#!/usr/bin/env python
# encoding: utf-8

################################################################################
#
#   RMG - Reaction Mechanism Generator
#
#   Copyright (c) 2009-2011 by the RMG Team (rmg_dev@mit.edu)
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the 'Software'),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.
#
################################################################################


"""
This module contains functions for load existing RMG simulations
by reading in files.
"""
import os.path

from rmgpy.chemkin import loadChemkinFile

from rmgpy.solver.base import TerminationTime, TerminationConversion

def loadRMGJob(inputFile, chemkinFile=None, speciesDict=None, generateImages=True, useJava=False, useChemkinNames=False):

    if useJava:
        # The argument is an RMG-Java input file
        rmg = loadRMGJavaJob(inputFile, chemkinFile, speciesDict, generateImages, useChemkinNames=useChemkinNames)
        
    else:
        # The argument is an RMG-Py input file
        rmg = loadRMGPyJob(inputFile, chemkinFile, speciesDict, generateImages, useChemkinNames=useChemkinNames)

    return rmg

def loadRMGPyJob(inputFile, chemkinFile=None, speciesDict=None, generateImages=True, useChemkinNames=False):
    """
    Load the results of an RMG-Py job generated from the given `inputFile`.
    """
    from rmgpy.rmg.main import RMG
    
    # Load the specified RMG input file
    rmg = RMG(inputFile=inputFile)
    rmg.loadInput(inputFile)
    rmg.outputDirectory = os.path.abspath(os.path.dirname(inputFile))
    
    # Load the final Chemkin model generated by RMG
    if not chemkinFile:
        chemkinFile = os.path.join(os.path.dirname(inputFile), 'chemkin', 'chem.inp')
    if not speciesDict:
        speciesDict = os.path.join(os.path.dirname(inputFile), 'chemkin', 'species_dictionary.txt')
    speciesList, reactionList = loadChemkinFile(chemkinFile, speciesDict, useChemkinNames=useChemkinNames)
    
    # Map species in input file to corresponding species in Chemkin file
    speciesDict = {}
    for spec0 in rmg.initialSpecies:
        for species in speciesList:
            if species.isIsomorphic(spec0):
                speciesDict[spec0] = species
                break
            
    # Generate flux pairs for each reaction if needed
    for reaction in reactionList:
        if not reaction.pairs: reaction.generatePairs()
    
    # Replace species in input file with those in Chemkin file
    for reactionSystem in rmg.reactionSystems:
        reactionSystem.initialMoleFractions = dict([(speciesDict[spec], frac) for spec, frac in reactionSystem.initialMoleFractions.iteritems()])
        for t in reactionSystem.termination:
            if isinstance(t, TerminationConversion):
                t.species = speciesDict[t.species]
        reactionSystem.sensitiveSpecies = [speciesDict[spec] for spec in reactionSystem.sensitiveSpecies]
    
    # Set reaction model to match model loaded from Chemkin file
    rmg.reactionModel.core.species = speciesList
    rmg.reactionModel.core.reactions = reactionList

    # Generate species images
    if generateImages:
        speciesPath = os.path.join(os.path.dirname(inputFile), 'species')
        try:
            os.mkdir(speciesPath)
        except OSError:
            pass
        for species in speciesList:
            path = os.path.join(speciesPath, '{0!s}.png'.format(species))
            if not os.path.exists(path):
                species.molecule[0].draw(str(path))
    
    return rmg

def loadRMGJavaJob(inputFile, chemkinFile=None, speciesDict=None, useChemkinNames=False):
    """
    Load the results of an RMG-Java job generated from the given `inputFile`.
    """
    from rmgpy.rmg.main import RMG
    from rmgpy.molecule import Molecule
    
    # Load the specified RMG-Java input file
    # This implementation only gets the information needed to generate flux diagrams
    rmg = RMG(inputFile=inputFile)
    rmg.loadRMGJavaInput(inputFile)
    rmg.outputDirectory = os.path.abspath(os.path.dirname(inputFile))
    
    # Load the final Chemkin model generated by RMG-Java
    if not chemkinFile:
        chemkinFile = os.path.join(os.path.dirname(inputFile), 'chemkin', 'chem.inp')
    if not speciesDict:
        speciesDict = os.path.join(os.path.dirname(inputFile), 'RMG_Dictionary.txt')
    speciesList, reactionList = loadChemkinFile(chemkinFile, speciesDict, useChemkinNames=useChemkinNames)
    
    # Bath gas species don't appear in RMG-Java species dictionary, so handle
    # those as a special case
    for species in speciesList:
        if species.label == 'Ar':
            species.molecule = [Molecule().fromSMILES('[Ar]')]
        elif species.label == 'Ne':
            species.molecule = [Molecule().fromSMILES('[Ne]')]
        elif species.label == 'He':
            species.molecule = [Molecule().fromSMILES('[He]')]
        elif species.label == 'N2':
            species.molecule = [Molecule().fromSMILES('N#N')]
    
    # Map species in input file to corresponding species in Chemkin file
    speciesDict = {}
    for spec0 in rmg.initialSpecies:
        for species in speciesList:
            if species.isIsomorphic(spec0):
                speciesDict[spec0] = species
                break
            
    # Generate flux pairs for each reaction if needed
    for reaction in reactionList:
        if not reaction.pairs: reaction.generatePairs()

    # Replace species in input file with those in Chemkin file
    for reactionSystem in rmg.reactionSystems:
        reactionSystem.initialMoleFractions = dict([(speciesDict[spec], frac) for spec, frac in reactionSystem.initialMoleFractions.iteritems()])
        for t in reactionSystem.termination:
            if isinstance(t, TerminationConversion):
                if t.species not in speciesDict.values():
                    t.species = speciesDict[t.species]
    
    # Set reaction model to match model loaded from Chemkin file
    rmg.reactionModel.core.species = speciesList
    rmg.reactionModel.core.reactions = reactionList
    
    # RMG-Java doesn't generate species images, so draw them ourselves now
    speciesPath = os.path.join(os.path.dirname(inputFile), 'species')
    try:
        os.mkdir(speciesPath)
    except OSError:
        pass
    for species in speciesList:

        path = os.path.join(speciesPath + '/{0!s}.png'.format(species))
        species.molecule[0].draw(str(path))
    
    return rmg

