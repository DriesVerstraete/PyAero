import sys
import copy
import webbrowser

import PySide2
from PySide2 import QtGui, QtCore, QtWidgets

import PyAero
import Airfoil
import FileDialog
import GraphicsTest
from Settings import DIALOGFILTER, AIRFOILDATA, DEFAULT_CONTOUR
import logging
logger = logging.getLogger(__name__)


class Slots:
    """This class handles all callback routines for GUI actions

    PyQt uses signals and slots for GUI events and their respective
    handlers/callbacks.
    """

    def __init__(self, parent):
        """Constructor for Slots class

        Args:
            parent (QMainWindow object): MainWindow instance
        """
        self.parent = parent

    def onOpen(self):
        """Summary

        Returns:
            TYPE: Description
        """
        file_dialog = FileDialog.Dialog()
        file_dialog.setFilter(DIALOGFILTER)
        filename, _ = file_dialog.openFilename(directory=AIRFOILDATA)

        if not filename:
            logger.info('No file selected. Nothing saved.')
            return

        if 'su2' in filename:
            self.loadSU2(filename)
            return

        self.loadAirfoil(filename)

    def onOpenPredefined(self):
        self.loadAirfoil(DEFAULT_CONTOUR)

    def loadAirfoil(self, filename, comment='#'):
        fileinfo = QtCore.QFileInfo(filename)
        name = fileinfo.fileName()

        airfoil = Airfoil.Airfoil(name)
        loaded = airfoil.readContour(filename, comment)

        # no error during loading
        if loaded:
            # clear all items from the scene when new airfoil is loaded
            self.parent.scene.clear()
            # make contour, markers, chord and add everything to the scene
            airfoil.makeAirfoil()
            # add all airfoil items (contour markers) to the scene
            Airfoil.Airfoil.addToScene(airfoil, self.parent.scene)
            # make loaded airfoil the currently active airfoil
            self.parent.airfoil = airfoil
            # add airfoil to list of loaded airfoils
            self.parent.airfoils.append(airfoil)
            # automatically zoom airfoil so that it fits into the view
            self.fitAirfoilInView()
            logger.info('Airfoil {} loaded'.format(name))

            self.parent.centralwidget.toolbox.header.setEnabled(True)
            self.parent.centralwidget.toolbox.listwidget.setEnabled(True)
            self.parent.centralwidget.toolbox.listwidget.addItem(name)

    def loadSU2(self, filename):
        comment = '%'

        try:
            with open(filename, mode='r') as f:
                lines = f.readlines()
        except IOError as error:
            # exc_info=True sends traceback to the logger
            logger.error('Failed to open file {} with error {}'.
                         format(filename, error), exc_info=True)
            return False

        # FIXME
        # FIXME
        # FIXME
        data = [line for line in lines if comment not in line]

    def fitAirfoilInView(self):

        if len(self.parent.airfoils) == 0:
            return

        # get bounding rect in scene coordinates
        item = self.parent.airfoil.contourPolygon
        rectf = item.boundingRect()
        rf = copy.deepcopy(rectf)

        center = rf.center()
        # make 4% smaller than width of graphicsview
        w = 1.04 * rf.width()
        h = 1.04 * rf.height()
        # do not use setWidhtF and setHeightF here!!!
        rf.setWidth(w)
        rf.setHeight(h)

        # shift center of rectf
        cx = center.x()
        cy = center.y()
        rf.moveCenter(QtCore.QPointF(cx, cy))

        self.parent.view.fitInView(rf,
                                   aspectRadioMode=QtCore.Qt.KeepAspectRatio)

        # it is IMPORTANT that this is called after fitInView
        # adjust airfoil marker size to MARKERSIZE setting
        self.parent.view.adjustMarkerSize()

        # cache view to be able to keep it during resize
        self.parent.view.getSceneFromView()

    def onViewAll(self):
        """zoom inorder to view all items in the scene"""

        # take all items except markers (as they are adjusted in size for view)

        rectf = self.parent.scene.itemsBoundingRect()
        self.parent.view.fitInView(rectf,
                                   aspectRadioMode=QtCore.Qt.KeepAspectRatio)

        # it is IMPORTANT that this is called after fitInView
        # adjust airfoil marker size to MARKERSIZE setting
        self.parent.view.adjustMarkerSize()

        # cache view to be able to keep it during resize
        self.parent.view.getSceneFromView()

    def toggleTestObjects(self):
        if self.parent.testitems:
            GraphicsTest.deleteTestItems(self.parent.scene)
            logger.info('Test items for GraphicsView loaded')
        else:
            GraphicsTest.addTestItems(self.parent.scene)
            logger.info('Test items for GraphicsView removed')
        self.parent.testitems = not self.parent.testitems

    def onSave(self):
        (fname, thefilter) = QtWidgets.QFileDialog. \
            getSaveFileNameAndFilter(self.parent,
                                     'Save file', '.', filter=DIALOGFILTER)
        if not fname:
            return

        with open(fname, 'w') as f:
            f.write('This test worked for me ...')

    def onSaveAs(self):
        (fname, thefilter) = QtGui. \
            QFileDialog.getSaveFileNameAndFilter(
            self.parent, 'Save file as ...', '.',
            filter=DIALOGFILTER)
        if not fname:
            return
        with open(fname, 'w') as f:
            f.write('This test worked for me ...')

    def onPrint(self):
        dialog = QtGui.QPrintDialog()
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.parent.editor.document().print_(dialog.printer())

    def onPreview(self):
        printer = QtGui.QPrinter(QtGui.QPrinter.HighResolution)

        preview = QtGui.QPrintPreviewDialog(printer, self.parent)
        preview.paintRequested.connect(self.handlePaintRequest)
        preview.exec_()

    # setup printer for print preview
    def handlePaintRequest(self, printer):
        printer.setOrientation(QtGui.QPrinter.Landscape)
        self.parent.view.render(QtGui.QPainter(printer))

    def toggleLogDock(self, _sender):
        """Switch message log window on/off"""

        logger.debug('I am toggleLogDock')
        logger.debug('This is _sender: {}'.format(_sender))

        visible = self.parent.messagedock.isVisible()
        self.parent.messagedock.setVisible(not visible)

        # update the checkbox if toggling is done via keyboard shortcut
        if _sender == 'shortcut':
            checkbox = self.parent.centralwidget.cb1
            checkbox.setChecked(not checkbox.isChecked())

    def onBlockMesh(self):
        pass

    def getAirfoilByName(self, name):
        for airfoil in self.parent.airfoils:
            if airfoil.name == name:
                return airfoil
        return None

    def removeAirfoil(self, name=None):
        """Remove all selected airfoils from the scene"""

        # the name parameter is only set when coming from listwidget
        # and the deleting is done via DEL key
        if name:
            airfoil = self.getAirfoilByName(name)
        else:
            airfoil = self.parent.airfoil

        # remove airfoil from the list in the list widget
        self.parent.airfoils.remove(airfoil)

        # remove from scene only if active airfoil was chosen
        if airfoil.name == self.parent.airfoil.name:
            # removes all items from the scene (polygon, chord, mesh, etc.)
            self.parent.scene.clear()

        # remove also listwidget entry
        centralwidget = self.parent.centralwidget
        listwidget = centralwidget.toolbox.listwidget
        itms = listwidget.findItems(
            self.parent.airfoil.name, QtCore.Qt.MatchExactly)
        for itm in itms:
            row = listwidget.row(itm)
            listwidget.takeItem(row)

        # fit all remaining scene items into the view
        self.onViewAll()

    def onMessage(self, msg):
        # move cursor to the end before writing new message
        # so in case text inside the log window was selected before
        # the new text is pastes correct
        self.parent.messages.moveCursor(QtGui.QTextCursor.End)
        self.parent.messages.append(msg)

    def onExit(self):
        sys.exit(QtWidgets.qApp.quit())

    def onCalculator(self):
        pass

    def onBackground(self):
        if self.parent.view.viewstyle == 'gradient':
            self.parent.view.viewstyle = 'solid'
        else:
            self.parent.view.viewstyle = 'gradient'

        self.parent.view.setBackground(self.parent.view.viewstyle)

    def onUndo(self):
        pass

    def onLevelChanged(self):
        """Change size of message window when floating """
        if self.parent.messagedock.isFloating():
            self.parent.messagedock.resize(600, 300)

    def onTextChanged(self):
        """Move the scrollbar in the message log-window to the bottom.
        So latest messages are always in the view.
        """
        vbar = self.parent.messages.verticalScrollBar()
        if vbar:
            vbar.triggerAction(QtWidgets.QAbstractSlider.SliderToMaximum)

    def onTabChanged(self):
        """Sync tabs and toolboxes """
        tabs = self.parent.centralwidget.tabs
        tab_text = self.parent.centralwidget.tabs.tabText(tabs.currentIndex())
        toolbox = self.parent.centralwidget.toolbox

        if tab_text == 'Airfoil Viewer':
            toolbox.setCurrentIndex(toolbox.tb1)
        if tab_text == 'Contour Analysis':
            toolbox.setCurrentIndex(toolbox.tb3)

    def messageBox(self, message):
        QtWidgets.QMessageBox. \
            information(self.parent, 'Information',
                        message, QtWidgets.QMessageBox.Ok)

    def onRedo(self):
        pass

    def onHelp(self):
        pass

    def onHelpOnline(self):
        webbrowser.open('http://pyaero.readthedocs.io/en/latest/')

    def onAbout(self):
        QtWidgets.QMessageBox. \
            about(self.parent, "About " + PyAero.__appname__,
                  "<b>" + PyAero.__appname__ +
                  "</b> is used for "
                  "2D airfoil contour analysis and CFD mesh generation.\
                  <br><br>"
                  "<b>" + PyAero.__appname__ + "</b> code under " +
                  PyAero.__license__ +
                  " license. (c) " +
                  PyAero.__copyright__ + "<br><br>"
                  "email to: " + PyAero.__email__ + "<br><br>"
                  "Embedded <b>Aeropython</b> code under MIT license. <br> \
                  (c) 2014 Lorena A. Barba, Olivier Mesnard<br>"
                  "Link to " +
                  "<a href='http://nbviewer.ipython.org/github/" +
                  "barbagroup/AeroPython/blob/master/lessons/" +
                  "11_Lesson11_vortexSourcePanelMethod.ipynb'> \
                  <b>Aeropython</b></a> (iPython notebook)." + "<br><br>"
                  + "<b>VERSIONS:</b>" + "<br>"
                  + PyAero.__appname__ + ": " + PyAero.__version__ +
                  "<br>"
                  + "Python: %s" % (sys.version.split()[0]) + "<br>"
                  + "Qt for Python: %s" % (PySide2.__version__) + "<br>"
                  + "Qt: %s" % (PySide2.QtCore.__version__)
                  )
