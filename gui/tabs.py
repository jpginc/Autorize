import sys
sys.path.append("..")

from java.awt.datatransfer import StringSelection
from javax.swing.table import TableRowSorter
from java.awt.event import AdjustmentListener
from java.awt.event import ActionListener
from javax.swing import JSplitPane
from javax.swing import JMenuItem
from javax.swing import JScrollPane
from javax.swing import JPopupMenu
from javax.swing import JTabbedPane
from java.awt import Toolkit
from java.lang import Math

from burp import ITab
from burp import IMessageEditorController

from thread import start_new_thread

from table.table import Table, LogEntry, TableRowFilter

class ITabImpl(ITab):
    def __init__(self, extender):
        self._extender = extender

    def getTabCaption(self):
        return "Autorize"
    
    def getUiComponent(self):
        return self._extender._splitpane

class Tabs():
    def __init__(self, extender):
        self._extender = extender

    def draw(self):
        """  init autorize tabs
        """

        self._extender.logTable = Table(self._extender)

        #self.logTable.setAutoCreateRowSorter(True)

        tableWidth = self._extender.logTable.getPreferredSize().width        
        self._extender.logTable.getColumn("ID").setPreferredWidth(Math.round(tableWidth / 50 * 2))
        self._extender.logTable.getColumn("Method").setPreferredWidth(Math.round(tableWidth / 50 * 3))
        self._extender.logTable.getColumn("URL").setPreferredWidth(Math.round(tableWidth / 50 * 25))
        self._extender.logTable.getColumn("Orig. Length").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self._extender.logTable.getColumn("Modif. Length").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self._extender.logTable.getColumn("Unauth. Length").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self._extender.logTable.getColumn("Authorization Enforcement Status").setPreferredWidth(Math.round(tableWidth / 50 * 4))
        self._extender.logTable.getColumn("Authorization Unauth. Status").setPreferredWidth(Math.round(tableWidth / 50 * 4))

        self._extender.tableSorter = TableRowSorter(self._extender.tableModel)
        rowFilter = TableRowFilter(self._extender)
        self._extender.tableSorter.setRowFilter(rowFilter)
        self._extender.logTable.setRowSorter(self._extender.tableSorter)

        self._extender._splitpane = JSplitPane(JSplitPane.HORIZONTAL_SPLIT)
        self._extender._splitpane.setResizeWeight(1)
        self._extender.scrollPane = JScrollPane(self._extender.logTable)
        self._extender._splitpane.setLeftComponent(self._extender.scrollPane)
        self._extender.scrollPane.getVerticalScrollBar().addAdjustmentListener(AutoScrollListener(self._extender))

        copyURLitem = JMenuItem("Copy URL")
        copyURLitem.addActionListener(CopySelectedURL(self._extender))

        sendRequestMenu = JMenuItem("Send Original Request to Repeater")
        sendRequestMenu.addActionListener(SendRequestRepeater(self._extender, self._extender._callbacks, True))

        sendRequestMenu2 = JMenuItem("Send Modified Request to Repeater")
        sendRequestMenu2.addActionListener(SendRequestRepeater(self._extender, self._extender._callbacks, False))

        sendResponseMenu = JMenuItem("Send Responses to Comparer")
        sendResponseMenu.addActionListener(SendResponseComparer(self._extender, self._extender._callbacks))

        retestSelecteditem = JMenuItem("Retest selected request")
        retestSelecteditem.addActionListener(RetestSelectedRequest(self._extender))
        
        deleteSelectedItem = JMenuItem("Delete")
        deleteSelectedItem.addActionListener(DeleteSelectedRequest(self._extender))

        self._extender.menu = JPopupMenu("Popup")
        self._extender.menu.add(sendRequestMenu)
        self._extender.menu.add(sendRequestMenu2)
        self._extender.menu.add(sendResponseMenu)
        self._extender.menu.add(copyURLitem)
        self._extender.menu.add(retestSelecteditem)
        # self.menu.add(deleteSelectedItem) disabling this feature until bug will be fixed.
        message_editor = MessageEditor(self._extender)

        self._extender.tabs = JTabbedPane()
        self._extender._requestViewer = self._extender._callbacks.createMessageEditor(message_editor, False)
        self._extender._responseViewer = self._extender._callbacks.createMessageEditor(message_editor, False)

        self._extender._originalrequestViewer = self._extender._callbacks.createMessageEditor(message_editor, False)
        self._extender._originalresponseViewer = self._extender._callbacks.createMessageEditor(message_editor, False)

        self._extender._unauthorizedrequestViewer = self._extender._callbacks.createMessageEditor(message_editor, False)
        self._extender._unauthorizedresponseViewer = self._extender._callbacks.createMessageEditor(message_editor, False)        

        self._extender.tabs.addTab("Modified Request", self._extender._requestViewer.getComponent())
        self._extender.tabs.addTab("Modified Response", self._extender._responseViewer.getComponent())

        self._extender.tabs.addTab("Original Request", self._extender._originalrequestViewer.getComponent())
        self._extender.tabs.addTab("Original Response", self._extender._originalresponseViewer.getComponent())

        self._extender.tabs.addTab("Unauthenticated Request", self._extender._unauthorizedrequestViewer.getComponent())
        self._extender.tabs.addTab("Unauthenticated Response", self._extender._unauthorizedresponseViewer.getComponent())        

        self._extender.tabs.addTab("Configuration", self._extender.pnl)
        self._extender.tabs.setSelectedIndex(6)
        self._extender._splitpane.setRightComponent(self._extender.tabs)


class SendRequestRepeater(ActionListener):
    def __init__(self, extender, callbacks, original):
        self._extender = extender
        self._callbacks = callbacks
        self.original = original

    def actionPerformed(self, e):
        if self.original:
                request = self._extender._currentlyDisplayedItem._originalrequestResponse
        else:
                request = self._extender._currentlyDisplayedItem._requestResponse
        host = request.getHttpService().getHost()
        port = request.getHttpService().getPort()
        
        self._callbacks.sendToRepeater(host, port, 1, request.getRequest(), "Autorize");

class SendResponseComparer(ActionListener):
    def __init__(self, extender, callbacks):
        self._extender = extender
        self._callbacks = callbacks

    def actionPerformed(self, e):
        originalResponse = self._extender._currentlyDisplayedItem._originalrequestResponse
        modifiedResponse = self._extender._currentlyDisplayedItem._requestResponse
        unauthorizedResponse = self._extender._currentlyDisplayedItem._unauthorizedRequestResponse
        
        self._callbacks.sendToComparer(originalResponse.getResponse());
        self._callbacks.sendToComparer(modifiedResponse.getResponse());
        self._callbacks.sendToComparer(unauthorizedResponse.getResponse());


class RetestSelectedRequest(ActionListener):
    def __init__(self, extender):
        self._extender = extender

    def actionPerformed(self, e):
        start_new_thread(self._extender.checkAuthorization, (self._extender._currentlyDisplayedItem._originalrequestResponse, self._extender._helpers.analyzeResponse(self._extender._currentlyDisplayedItem._originalrequestResponse.getResponse()).getHeaders(), self._extender.doUnauthorizedRequest.isSelected()))

class DeleteSelectedRequest(ActionListener):
    def __init__(self, extender):
        self._extender = extender

    def actionPerformed(self, e): # bug after first deletion!
        pass
        # logBackup = self._extender._log[:]
        # self._extender.clearList(self)
        # self._extender._lock.acquire()
        # print self._extender._currentlyDisplayedItem
        # logBackup.remove(self._extender._currentlyDisplayedItem)
        # self._extender._log = logBackup
        # row = self._extender._log.size()
        # start_new_thread(self._extender.UpdateTableEDT, (self._extender,"insert",row,row))
        # SwingUtilities.invokeLater(UpdateTableEDT(self._extender,"delete",0, oldSize - 1))
        # self._extender._lock.release()

class CopySelectedURL(ActionListener):
    def __init__(self, extender):
        self._extender = extender

    def actionPerformed(self, e):
        stringSelection = StringSelection(str(self._extender._helpers.analyzeRequest(self._extender._currentlyDisplayedItem._requestResponse).getUrl()))
        clpbrd = Toolkit.getDefaultToolkit().getSystemClipboard()
        clpbrd.setContents(stringSelection, None)

class AutoScrollListener(AdjustmentListener):
    def __init__(self, extender):
        self._extender = extender

    def adjustmentValueChanged(self, e):
        if self._extender.autoScroll.isSelected():
            e.getAdjustable().setValue(e.getAdjustable().getMaximum())

class MessageEditor(IMessageEditorController):
    def __init__(self, extender):
        pass

    def getHttpService(self):
        return self._extender._currentlyDisplayedItem.getHttpService()

    def getRequest(self):
        return self._extender._currentlyDisplayedItem.getRequest()

    def getResponse(self):
        return self._extender._currentlyDisplayedItem.getResponse()
        