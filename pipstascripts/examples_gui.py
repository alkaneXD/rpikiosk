# examples_gui.py
# $Rev$
# Copyright (c) 2015 Able Systems Limited. All rights reserved.
'''This code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This python code uses pyqt4 to provide a simple GUI for launching
some of the example provided with the Pipsta.

Copyright (c) 2015, Able Systems Ltd. All rights reserved.
'''
import sys
from PyQt4.QtGui import QApplication, QMessageBox, QDialog
from PyQt4.QtCore import QUrl, QProcess, pyqtSlot
from launcher import config, ExampleWidgetFactory
from PyQt4 import uic

class ExampleLauncher(
        QDialog,
        uic.loadUiType("launcher/ExampleLauncher.ui")[0]
    ):
    '''A Qt Dialog (described in launcher/ExampleLauncher.ui) that is
    used to colect user input required to launch a configured example
    from the Pipsta demoes.'''
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        self.__examples = []
        self.examplesComboBox.currentIndexChanged.connect(
            self.__set_current_example_index
        )
        self.printButton.clicked.connect(self.__launch_example)

    @pyqtSlot()            
    def __launch_example(self):
        '''Called when the user presses the 'Print' button.  Launches
        ther configured example with the arguments presented by the UI.
        '''
        example = self.examplesComboBox.itemData(
            self.examplesComboBox.currentIndex()
        ).toPyObject()

        try:
            cmd = 'python {0} {1}'.format(
                QUrl(example.script_file).toLocalFile(),
                self.inputWidget.currentWidget().args()
            )
            print(cmd)
            proc = QProcess()
            proc.start(cmd)
            proc.waitForFinished()
        except UnicodeDecodeError as _unknown:
            QMessageBox.information(self,
                'Font Problem',
                'There was a problem decoding some of the font '
                'information. Print has been cancelled.')

    def __query_quit(self):
        '''Ensure the same dialog is displayed for all quit
        mechanisms'''
        return QMessageBox.question(self, 'Quit ...',
            'Are you sure you want to quit?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

    # pylint: disable=C0103
    def closeEvent(self, event):
        '''Called by the Qt framework when the user attempts to quit the
        application'''
        reply = self.__query_quit()

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def set_examples(self, new_examples):
        '''The main application uses this method to load all of the
        examples listed in the configuration into the UI.'''
        self.__examples = new_examples
        self.examplesComboBox.clear()

        for example in self.__examples:
            self.examplesComboBox.addItem(example.name, example)

    @pyqtSlot()
    def reject(self):
        '''Called when the user attempts to dismiss the main dialog.'''
        msg_box_result = self.__query_quit()

        if msg_box_result == QMessageBox.Yes:
            return super(ExampleLauncher, self).reject()

    @pyqtSlot(int)
    def __set_current_example_index(self, index):
        '''When the user selects an example in the drop-down combo-box
        this method is called.  This method brings the examples
        configuration to the fore.'''
        example = self.examplesComboBox.itemData(index).toPyObject()
        self.titleLabel.setText(example.name)
        self.descriptionLabel.setText(example.description)
        
        self.printButton.setEnabled(True)

        self.inputWidget.setCurrentIndex(self.examplesComboBox.currentIndex())
        
        
def main():
    '''Instantiated the main application and the main dialog, then
    displays the main dialog.  Loads all of the examples from the config
    files and adds the matching GUI components to the main dialog.'''
    app = QApplication(sys.argv)
    view = ExampleLauncher()

    for example in config.EXAMPLES:
        view.inputWidget.addWidget(
            ExampleWidgetFactory.get_editor_for_name(
                example.editor_name
            )()
        )
    
    view.set_examples(config.EXAMPLES)
    view.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
