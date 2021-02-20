import os

import brick_gym.config as config
import brick_gym.ldraw.paths as ldraw_paths
from brick_gym.ldraw.commands import *
from brick_gym.ldraw.exceptions import *

class LDrawMissingFileComment(LDrawException):
    pass

class LDrawDocument:
    @staticmethod
    def parse_document(file_path, reference_table = None, shadow = False):
        file_name, ext = os.path.splitext(file_path)
        if ext == '.mpd' or ext == '.ldr':
            try:
                return LDrawMPDMainFile(file_path, reference_table, shadow)
            except LDrawMissingFileComment:
                return LDrawLDR(file_path, reference_table, shadow)
        # this doesn't work because a lot of ".ldr" files are actually
        # structured as ".mpd" files
        #elif ext == '.ldr':
        #    return LDrawLDR(file_path, reference_table, shadow)
        elif ext == '.dat':
            return LDrawDAT(file_path, reference_table, shadow)
    
    def set_reference_table(self, reference_table):
        if reference_table is None:
            reference_table = {'ldraw':{}, 'shadow':{}}
        self.reference_table = reference_table
        if self.shadow:
            self.reference_table['shadow'][self.reference_name] = self
        else:   
            self.reference_table['ldraw'][self.reference_name] = self
    
    def resolve_file_path(self, file_path):
        if self.shadow:
            self.resolved_file_path = ldraw_paths.resolve_shadow_path(file_path)
        else:
            self.resolved_file_path = ldraw_paths.resolve_ldraw_path(file_path)
    
    def import_references(self):
        for command in self.commands:
            # ldraw import commands
            if isinstance(command, (LDrawImportCommand, LDCadSnapInclCommand)):
            #if isinstance(command, LDrawImportCommand):
                reference_name = command.reference_name
                if reference_name not in self.reference_table['ldraw']:
                    try:
                        LDrawDocument.parse_document(
                                reference_name, self.reference_table)
                    except:
                        print('Error when importing: %s'%reference_name)
                        raise
            '''
            # ldcad SNAP_INCL commands
            if isinstance(command, LDCadSnapInclCommand):
                reference_name = command.reference_name
                if reference_name not in self.reference_table['shadow']:
                    try:
                        LDrawDocument.parse_document(
                                reference_name,
                                self.reference_table,
                                shadow=True)
                    except:
                        print('Error when importing: %s'%reference_name)
                        raise
            '''
            '''
            # ldcad SNAP_INCL commands
            if isinstance(command, LDCadSnapInclCommand):
                reference_name = command.reference_name
                if reference_name not in self.reference_table['shadow']:
                    try:
                        LDrawDocument.parse_document(
                                reference_name,
                                self.reference_table)
                    except:
                        print('Error when importing: %s'%reference_name)
                        raise
            '''
        
        # shadow
        if not self.shadow:
            if self.reference_name not in self.reference_table['shadow']:
                if self.reference_name in ldraw_paths.SHADOW_FILES:
                    try:
                        LDrawDocument.parse_document(
                                self.reference_name,
                                self.reference_table,
                                shadow=True)
                    except:
                        print('Error when importing shadow: %s'%
                                self.reference_name)
                        raise
    '''
    def brick_instances(self,
            reference_transform=None,
            reference_color=None):
        if reference_transform is None:
            reference_transform = numpy.eye(4)
        parts = []
        for command in self.commands:
            if isinstance(command, LDrawImportCommand):
                reference_name = command.reference_name
                reference_document = (
                        self.reference_table['ldraw'][reference_name])
                reference_transform = numpy.dot(
                        reference_transform, command.transform)
                reference_color = command.color
                if isinstance(reference_document, LDrawDAT):
                    if reference_name in ldraw_paths.LDRAW_PARTS:
                        parts.append(BrickInstance(
                                reference_document,
                                reference_transform,
                                reference_color))
                elif isinstance(reference_document, (
                        LDrawMPDMainFile,
                        LDrawMPDInternalFile,
                        LDrawLDR)):
                    parts.extend(reference_document.get_bricks(
                            reference_transform, reference_color))
                
        return parts
    '''

class LDrawMPDMainFile(LDrawDocument):
    def __init__(self, file_path, reference_table = None, shadow = False):
        
        # initialize reference_table
        self.shadow = shadow
        self.resolve_file_path(file_path)
        self.reference_name = ldraw_paths.get_reference_name(file_path)
        self.set_reference_table(reference_table)
        
        # resolve the file path and parse all commands in this file
        lines = open(self.resolved_file_path, encoding='latin-1').readlines()
        try:
            commands = LDrawCommand.parse_commands(lines)
        except:
            print('Error when parsing: %s'%self.reference_name)
            raise
        
        # make sure that the first line is a file comment
        if not len(commands):
            raise LDrawMissingFileComment(
                    'MPD file appears to be empty, must start with "0 FILE"')
        if not isinstance(commands[0], LDrawFileComment):
            raise LDrawMissingFileComment('MPD file must start with "0 FILE"')
        
        # split the commands into groups for each sub-file
        file_indices = [
                i for i in range(len(commands))
                if isinstance(commands[i], LDrawFileComment)]
        file_indices.append(len(commands))
        subfile_command_lists = [commands[start:end]
                for start, end in zip(file_indices[:-1], file_indices[1:])]
        
        # store the main file's commands
        self.commands = subfile_command_lists[0]
        
        # build internal files
        self.internal_files = [
                LDrawMPDInternalFile(subfile_commands, self.reference_table)
                for subfile_commands in subfile_command_lists[1:]]
        
        # import references
        # We must do this after creating the subfiles because the main file will
        # reference them, and so they need to be in the reference table.
        # Also, this MPDMainFile must take responsiblity to import the subfile
        # references because we need the full reference table filled with the
        # internal references before any of them bring in their external
        # references
        self.import_references()
        for internal_file in self.internal_files:
            internal_file.import_references()

class LDrawMPDInternalFile(LDrawDocument):
    def __init__(self, commands, reference_table = None):
        
        # make sure the commands list starts with a FILE comment
        if not isinstance(commands[0], LDrawFileComment):
            raise LDrawMissingFileComment(
                    'MPD Internal File must start with "0 FILE"')
        
        # initialize reference_table
        self.reference_name = commands[0].reference_name
        self.shadow = False
        self.set_reference_table(reference_table)
        
        # store commands
        self.commands = commands
        
class LDrawLDR(LDrawDocument):
    def __init__(self, file_path, reference_table = None, shadow = False):
        
        # initialize reference table
        self.shadow = shadow
        self.resolve_file_path(file_path)
        self.reference_name = ldraw_paths.get_reference_name(file_path)
        self.set_reference_table(reference_table)
        
        # resolve the file path and parse all commands in this file
        lines = open(
                self.resolved_file_path, encoding='latin-1').readlines()
        try:
            self.commands = LDrawCommand.parse_commands(lines)
        except:
            print('Error when parsing: %s'%self.reference_name)
            raise
        
        self.import_references()

class LDrawDAT(LDrawLDR):
    pass
