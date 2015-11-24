# Example.py
# $Rev$
# Copyright (c) 2015 Able Systems Limited. All rights reserved.
'''This code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

Copyright (c) 2015, Able Systems Ltd. All rights reserved.
'''

class Example:
    '''Basic data structure to carry information about an example. A
    set of methods exist to make it easy to create the example object.
    '''
    def __init__(self):
        self.name = ''
        self.script_file = ''
        self.description = ''
        self.editor_name = None

    def set_name(self, name):
        '''Sets the name of the example and returns a reference to self
        '''
        self.name = name
        return self

    def set_description(self, desc):
        '''Sets the description of the example and returns a reference
        to self'''
        self.description = desc
        return self

    def set_editor(self, editor):
        '''Sets the name of the editor to associate with the example and
        returns a reference to self'''
        self.editor_name = editor
        return self
        
    def set_script(self, script):
        '''Sets the name of the example script and returns a reference
        to self.'''
        self.script_file = script
        return self
