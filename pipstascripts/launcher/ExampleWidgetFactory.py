# ExampleWidgetFactory.py
# $Rev$
# Copyright (c) 2015 Able Systems Limited. All rights reserved.
'''This code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This is a simple factory that produces editor widgets for specific
examples.

Copyright (c) 2015, Able Systems Ltd. All rights reserved.
'''
from PyQt4 import uic
from PyQt4.QtGui import QWidget, QFileDialog, QPixmap, QFont
from PyQt4.QtGui import QFontDatabase
from PyQt4.QtCore import pyqtSlot
from fclist import fcmatch

class BaseWidget(QWidget):
    '''This class is a utility class that does some of the boiler plate
    Qt stuff.'''
    
    def __init__(self):
        '''Initialises the Qt based parent class'''
        QWidget.__init__(self)
        self.setupUi(self)
        
    def args(self):
        '''Contractually obliged to return a python string. Should
        probably be overridden.'''
        raise NotImplementedError(
            "Class {0} doesn't implement aMethod()".format(
                self.__class__.__name__
            )
        )

class SimpleTextWidget(
        BaseWidget,
        uic.loadUiType("launcher/SimpleTextWidget.ui")[0]
        ):
    '''This widget presents a single multi-line text edit to the user'''
    
    def args(self):
        '''Contractually obliged to return a python string'''
        return '"{0!s}"'.format(self.plainTextEdit.toPlainText())

class StyledTextWidget(
        BaseWidget, uic.loadUiType("launcher/StyledTextWidget.ui")[0]
    ):
    '''Presents a font selection dialog and a multi-line text edit, for
    the banners example.'''
    def __init__(self):
        '''Initialises the Qt based parent class'''
        BaseWidget.__init__(self)
        self.fontComboBox.setWritingSystem(QFontDatabase.Latin)
        index = self.fontComboBox.findText('FreeMono')
        if index != -1:
            self.fontComboBox.removeItem(index)
        index = self.fontComboBox.findText('FreeSans')
        if index != -1:
            self.fontComboBox.removeItem(index)
        index = self.fontComboBox.findText('FreeSerif')
        if index != -1:
            self.fontComboBox.removeItem(index)
        
        self.textEdit.setFontPointSize(24)

    @staticmethod
    def find_font_file(font):
        '''Uses fcmatch (python wrapper of fc-list functionality) to
        obtain system information about the selected font.  Namely the
        file name.'''
        print(font.family().toUtf8())
        font_details = fcmatch(str(font.family()))
        # pylint: disable=E1101
        return font_details.file

    def args(self):
        font_file = ''
        my_font = self.fontComboBox.currentFont()
        font_file = StyledTextWidget.find_font_file(my_font)
            
        return '"{0!s}" {1!s}'.format(self.textEdit.toPlainText(),
                                      font_file)
                                      
    @pyqtSlot(QFont)
    def change_to_new_font(self, font):
        '''This slot is called when the fontComboBox selection has
        changed.  The font is applied to the entire preview string,
        then focus is moved to the text edit.'''
        cursor = self.textEdit.textCursor()
        self.textEdit.selectAll()
        self.textEdit.setFont(font)
        self.textEdit.setFontPointSize(24)
        self.textEdit.setTextCursor(cursor)
        self.textEdit.setFocus()

class ImageSelectWidget(
        BaseWidget,
        uic.loadUiType("launcher/ImageSelectWidget.ui")[0]
        ):
    '''Presents a dialog that allows the user to select a PNG file and
    then displays a preview of the aforementioned graphic file.'''

    def args(self):
        '''Contractually obliged to return a python string'''
        return str(self.pathLabel.text())

    # pylint: disable=C0103
    @pyqtSlot()
    def openSelectImageFileDialog(self):
        '''This slot is called by the Ui_ImageSelectWidget (Qt-land)
        and is expected to display a file dialog and handle the result.
        '''
        filename = QFileDialog.getOpenFileName(
            self, 'Select Image File ...', 'Examples/8_Image_Print',
            'Images (*.png)'
        )

        if filename:
            # We have an image, present the filename and the preview
            # to the user.
            piccy = QPixmap(filename)
            self.imagePreviewLabel.setPixmap(piccy)
            self.pathLabel.setText(filename)

class MeritWidget(
        BaseWidget, uic.loadUiType("launcher/MeritWidget.ui")[0]
    ):
    '''Presents a dialog that alows a pupils name and a message to be
    entered for use in the production of a merit print out.'''
    
    def args(self):
        return '"{0!s}" "{1!s}"'.format(
            self.pupilLineEdit.text(),
            self.messageTextEdit.toPlainText())
            
def get_editor_for_name(name):
    '''Simple factory method that returns the widget requested by
    the configuration file via a string.'''
    
    return {'Text' : SimpleTextWidget,
            'StyledText' : StyledTextWidget,
            'Image' : ImageSelectWidget,
            'MeritForm' : MeritWidget,}[str(name)]
