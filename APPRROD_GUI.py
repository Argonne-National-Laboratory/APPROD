"""
______________________________________________________________________________
            --- --- --- --- --- --- --- --- --- --- --- --- ---
                A Python Program to Run RELAP5-3D On Demeter 
            --- --- --- --- --- --- --- --- --- --- --- --- ---        

                                Created by:

                       _____________________________
                      |           ______            |
                      |          /\    /\           |
                      |         /  \__/  \          |
                      |        /   /  \   \         |
                      |       /   /    \   \        |
                      |      /   /      \   \       |
                      |     /___/________\___\      |
                      |     \  /          \  /      |
                      |      \/____________\/       |
                      |                             |
                      | Argonne National Laboratory |
                      |_____________________________|
                      
                       For questions, please contact:
                   
                       Austin Grelle
                       agrelle@anl.gov

                       Argonne National Laboratory
                       Nuclear Engineering Division
                       9700 S. Cass Ave.
                       Argonne, Illinois 60439
______________________________________________________________________________

File: APPRROD_GUI.py
______________________________________________________________________________
Total files:
    APPRROD.py
  ->APPRROD_GUI.py
    APPRROD_Lib.py
    APPRROD_Threads.py

Functions in this File:
    Logo_Start(dc,CSCHEME = "Black",
    PRA_Branching_Start(dc,CSCHEME = "White",

Classes in this File:
    mainFrame(title = "APPRROD v0.01",)
        Functions:
            setLayoutPanels()
            createMenuBar()
            OnBranchingButton(event)
            OnServerButton(event)
            OnBText1(event)
            OnBText2(event)
            OnBText3(event)
            OnBText4(event)
            OnBText5(event)
            OnBText6(event)
            OnLoad(event)
            OnReset(event)
            OnExit(event)
            OnLicense(event)
            OnHelp(event)
            OnAbout(event)
    logoPanel(parent)
        Functions:
            InitBuffer(CSCHEME = "White", items = [])
            OnPaint(event)
            OnLeftDown(event)
            _startAnimation()
    panelThread(parent,)
        Functions:
            run()
            join(timeout=None)
            pause()
            _process()
    drawFrame(parent)
        Functions:
            createMenuBar()
            OnLoad(event)
            OnReset(event)
            OnExit(event)
            OnLicense(event)
            OnHelp(event)
            OnAbout(event)
    drawPanel(parent)
        Functions:
            OnWheel(event)
            OnLeftDown(event)
            OnMotion(event)
            InitBuffer(CSCHEME = "Black")
            OnPaint(event)
            OnSize(event)
"""

import wx, threading, sys, time, random
from APPRROD_Lib import *

class mainFrame(wx.Frame):

    def __init__(self, title = "APPRROD v0.01",):
        wx.Frame.__init__(self, None, title = "APPRROD v0.01",
                          size = (640,560),
                          style = wx.DEFAULT_FRAME_STYLE^wx.RESIZE_BORDER^wx.MAXIMIZE_BOX)
        try:
            icon = wx.Icon('APPRROD.ico', wx.BITMAP_TYPE_ICO,16,16)
            self.SetIcon(icon)
        except: pass
        self.parent = self
        self.threads = []
        self.status = False
        self.inputFile = None
        self.PRA_Branching_Start = None
        self.ServerStart = None
        
        self.configData = {'exe':'',
                           'args': '',
                           'inputFile': '',
                           'threads': '',
                           'workingDirectory':'',
                           'templateFile':''}
        
        if os.path.isfile(".Config"):
            self.configData.update(readConfigFile(".Config")[0])

        # Create the menu bar with a custom function
        self.createMenuBar()

        # Create the status bar
        self.setstatusbar = self.CreateStatusBar()

        # Create the layout of the GUI
        self.setLayoutPanels()

    def setLayoutPanels(self):
        self.panel = wx.Panel(self)
        self.panel.parent = self
        box = wx.BoxSizer(wx.VERTICAL)

        # The following commented-out code is a very "plain"
        # logo panel, if one desires not to use the 'logoPanel'
        self.panel_logo = logoPanel(self.panel)#wx.Panel(self.panel, style=wx.SUNKEN_BORDER)
##        panel_logo.SetBackgroundColour(wx.WHITE)
##        panel_logo_Sizer = wx.BoxSizer(wx.HORIZONTAL)
##        panel1 = wx.Panel(panel_logo)
##        try:
##            image1 = wx.Image("APPRROD.ico", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
##            wx.StaticBitmap(panel1, -1, image1)
##        except: pass
##        panel2 = wx.Panel(panel_logo)
##        text2 = wx.StaticText(panel2, -1, label="APPRROD v0.01",style = wx.ALIGN_CENTER,)
##        panel_logo_Sizer.AddStretchSpacer(5)
##        panel_logo_Sizer.Add(panel1, 3, wx.EXPAND|wx.CENTER|wx.ALL)
##        panel_logo_Sizer.Add(panel2, 3, wx.EXPAND|wx.ALL)
##        panel_logo_Sizer.AddStretchSpacer(5)
##        panel_logo.SetSizer(panel_logo_Sizer)

        self.panel_info = wx.Panel(self.panel)
        self.panel_info_Sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_Sizer2 = wx.BoxSizer(wx.VERTICAL)

        self.panelBText1 = wx.Button(self.panel_info, -1, label = "BAT File", style = wx.EXPAND)
        self.panelBText2 = wx.Button(self.panel_info, -1, label = "License File", style = wx.EXPAND)
        self.panelBText3 = wx.Button(self.panel_info, -1, label = "Input File", style = wx.EXPAND)
        self.panelBText4 = wx.Button(self.panel_info, -1, label = "# of Threads", style = wx.EXPAND)
        self.panelBText5 = wx.Button(self.panel_info, -1, label = "Working Directory", style = wx.EXPAND)
        self.panelBText6 = wx.Button(self.panel_info, -1, label = "Template File", style = wx.EXPAND)
        self.Bind(wx.EVT_BUTTON, self.OnBText1, self.panelBText1)
        self.Bind(wx.EVT_BUTTON, self.OnBText2, self.panelBText2)
        self.Bind(wx.EVT_BUTTON, self.OnBText3, self.panelBText3)
        self.Bind(wx.EVT_BUTTON, self.OnBText4, self.panelBText4)
        self.Bind(wx.EVT_BUTTON, self.OnBText5, self.panelBText5)
        self.Bind(wx.EVT_BUTTON, self.OnBText6, self.panelBText6)
        self.panelSText1 = wx.StaticText(self.panel_info, -1, self.configData['batFile'])
        self.panelSText2 = wx.StaticText(self.panel_info, -1, self.configData['licenseFile'])
        self.panelSText3 = wx.StaticText(self.panel_info, -1, self.configData['inputFile'])
        self.panelSText4 = wx.SpinCtrl(self.panel_info, -1, self.configData['threads'])
        self.panelSText5 = wx.StaticText(self.panel_info, -1, self.configData['workingDirectory'])
        self.panelSText6 = wx.StaticText(self.panel_info, -1, self.configData['templateFile'])
        
        self.panel_info_Sizer2.AddStretchSpacer(1)
        self.panel_info_SizerT = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_SizerT.Add(self.panelBText1, 4, wx.EXPAND|wx.ALL)
        self.panel_info_SizerT.AddStretchSpacer(1)
        self.panel_info_SizerT.Add(self.panelSText1, 18, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.Add(self.panel_info_SizerT, 2, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.AddStretchSpacer(1)
        self.panel_info_SizerT = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_SizerT.Add(self.panelBText2, 4, wx.EXPAND|wx.ALL)
        self.panel_info_SizerT.AddStretchSpacer(1)
        self.panel_info_SizerT.Add(self.panelSText2, 18, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.Add(self.panel_info_SizerT, 2, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.AddStretchSpacer(1)
        self.panel_info_SizerT = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_SizerT.Add(self.panelBText3, 4, wx.EXPAND|wx.ALL)
        self.panel_info_SizerT.AddStretchSpacer(1)
        self.panel_info_SizerT.Add(self.panelSText3, 18, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.Add(self.panel_info_SizerT, 2, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.AddStretchSpacer(1)
        self.panel_info_SizerT = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_SizerT.Add(self.panelBText4, 4, wx.EXPAND|wx.ALL)
        self.panel_info_SizerT.AddStretchSpacer(1)
        self.panel_info_SizerT.Add(self.panelSText4, 18, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.Add(self.panel_info_SizerT, 2, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.AddStretchSpacer(1)
        self.panel_info_SizerT = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_SizerT.Add(self.panelBText5, 4, wx.EXPAND|wx.ALL)
        self.panel_info_SizerT.AddStretchSpacer(1)
        self.panel_info_SizerT.Add(self.panelSText5, 18, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.Add(self.panel_info_SizerT, 2, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.AddStretchSpacer(1)
        self.panel_info_SizerT = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_info_SizerT.Add(self.panelBText6, 4, wx.EXPAND|wx.ALL)
        self.panel_info_SizerT.AddStretchSpacer(1)
        self.panel_info_SizerT.Add(self.panelSText6, 18, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.Add(self.panel_info_SizerT, 2, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer2.AddStretchSpacer(1)

        self.panel_info_Sizer1.AddStretchSpacer(1)
        self.panel_info_Sizer1.Add(self.panel_info_Sizer2, 7, wx.EXPAND|wx.ALL)
        self.panel_info_Sizer1.AddStretchSpacer(1)
        self.panel_info.SetSizer(self.panel_info_Sizer1)
        
        self.panel_buttons = wx.Panel(self.panel)
        panel_buttons_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.branchingButton = wx.Button(self.panel_buttons, -1, label="Open Branching Viewer", size=(200,50),style=wx.EXPAND)
        self.Bind(wx.EVT_BUTTON, self.OnBranchingButton, self.branchingButton)
        self.serverButton = wx.Button(self.panel_buttons, -1, label="Start the Server", size=(200,50),style=wx.EXPAND)
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: self.serverButton.Disable()
        self.Bind(wx.EVT_BUTTON, self.OnServerButton, self.serverButton)
        panel_buttons_Sizer.AddStretchSpacer(1)
        panel_buttons_Sizer.Add(self.branchingButton,3,wx.EXPAND|wx.CENTER|wx.ALL)
        panel_buttons_Sizer.AddStretchSpacer(1)
        panel_buttons_Sizer.Add(self.serverButton,3,wx.EXPAND|wx.CENTER|wx.ALL)
        panel_buttons_Sizer.AddStretchSpacer(1)
        self.panel_buttons.SetSizer(panel_buttons_Sizer)
        
        box.Add(self.panel_logo, 6, wx.EXPAND|wx.ALL)
        box.AddStretchSpacer(1)
        box.Add(self.panel_info, 8, wx.EXPAND|wx.ALL)
        box.AddStretchSpacer(1)
        box.Add(self.panel_buttons, 4, wx.EXPAND|wx.CENTER|wx.ALL)
        box.AddStretchSpacer(1)
        
        self.panel.SetSizer(box)
        self.panel.Layout()
        self.panel_logo.InitBuffer()
        self.panel_logo._startAnimation()

    def createMenuBar(self):
        
        # Create a menu bar with File, Data, and Help elements
        menuBar = wx.MenuBar()
        # File menu contains Station Identification, Program Restart, and Program Exit
        file_menu = wx.Menu()
        loadFile = file_menu.Append(wx.ID_ANY, "&Load Input File\tAlt-L", "Load Input File (Current = " + str(self.inputFile) + " )")
        menuReset = file_menu.Append(wx.ID_REVERT, "&Restart Program\tAlt-R", "Reset all Program values")
        menuExit = file_menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
        # Data menu contains Total Number of Colloquiums, Option to Load Student ID file,
        #    Option to Load Attendance File(s), and if both Student ID file and Attendance files
        #    have been loaded, then an option to run a report.
        data_menu = wx.Menu()
        option1 = data_menu.Append(wx.ID_ANY, "&Option 1", "Option 1")
        # Help menu contains options to show the License, Help, or About information
        help_menu = wx.Menu()
        menuLicense = help_menu.Append(wx.ID_ANY, "&License", "View License information for this program.")
        menuHelp = help_menu.Append(wx.ID_HELP_CONTENTS, "&Help", "View program Help file.")
        menuAbout= help_menu.Append(wx.ID_ABOUT, "&About"," View information about this program.")
        # Append the three menu items and set the menu bar
        menuBar.Append(file_menu, "&File")
        menuBar.Append(data_menu, "&Data")
        menuBar.Append(help_menu, "&Help")
        self.SetMenuBar(menuBar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.OnLoad, loadFile)
        self.Bind(wx.EVT_MENU, self.OnReset, menuReset)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        
        self.Bind(wx.EVT_MENU, self.OnLicense, menuLicense)
        self.Bind(wx.EVT_MENU, self.OnHelp, menuHelp)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        
        self.Bind(wx.EVT_CLOSE, self.OnExit)

    def OnBranchingButton(self, event):
        if not self.PRA_Branching_Start:
            self.PRA_Branching_Start = drawFrame(self)
            self.PRA_Branching_Start.Show(True)
        else: self.PRA_Branching_Start.SetFocus()

    def OnServerButton(self, event):
        if not self.ServerStart:
            thread = serverMasterThread(self.configData)
            self.threads.append(thread)
            thread.start()
            self.serverButton.SetLabel("Turn Server Off")
            self.panel_buttons.Layout()
            self.ServerStart = True
        elif self.ServerStart:
            for thread in self.threads:
                if isinstance(thread,serverMasterThread):
                    thread.join()
                    break
            self.threads.remove(thread)
            self.serverButton.SetLabel("Start the Server")
            self.panel_buttons.Layout()
            self.ServerStart = False

    def OnBText1(self, event):
        dlg = wx.TextEntryDialog(self,
                                 message = "Enter a value for BAT File:",
                                 caption = "Configuration change",
                                 defaultValue = self.panelSText1.GetLabel(),
                                 )
        dlg.ShowModal()
        dlg.Destroy()
        value = dlg.GetValue()
        self.panelSText1.SetLabel(value)
        self.configData['exe'] = value
        self.panel_info.Layout()
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: return
        self.serverButton.Enable()

    def OnBText2(self, event):
        dlg = wx.TextEntryDialog(self,
                                 message = "Enter a value for License File:",
                                 caption = "Configuration change",
                                 defaultValue = self.panelSText2.GetLabel(),
                                 )
        dlg.ShowModal()
        dlg.Destroy()
        value = dlg.GetValue()
        self.panelSText2.SetLabel(value)
        self.configData['args'] = value
        self.panel_info.Layout()
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: return
        self.serverButton.Enable()

    def OnBText3(self, event):
        dlg = wx.TextEntryDialog(self,
                                 message = "Enter a value for Input File:",
                                 caption = "Configuration change",
                                 defaultValue = self.panelSText3.GetLabel(),
                                 )
        dlg.ShowModal()
        dlg.Destroy()
        value = dlg.GetValue()
        self.panelSText3.SetLabel(value)
        self.configData['inputFile'] = value
        self.panel_info.Layout()
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: return
        self.serverButton.Enable()

    def OnBText4(self, event):
        dlg = wx.TextEntryDialog(self,
                                 message = "Enter a value for # of Threads:",
                                 caption = "Configuration change",
                                 defaultValue = self.panelSText4.GetLabel(),
                                 )
        dlg.ShowModal()
        dlg.Destroy()
        value = dlg.GetValue()
        if value != '' and value.isdigit():
            self.panelSText4.SetValue(int(value))
            self.configData['threads'] = value
            self.panel_info.Layout()
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: return
        self.serverButton.Enable()

    def OnBText5(self, event):
        dlg = wx.TextEntryDialog(self,
                                 message = "Enter location for the Working Directory",
                                 caption = "Configuration change",
                                 defaultValue = self.panelSText5.GetLabel(),
                                 )
        dlg.ShowModal()
        dlg.Destroy()
        value = dlg.GetValue()
        self.panelSText5.SetLabel(value)
        self.configData['threads'] = value
        self.panel_info.Layout()
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: return
        self.serverButton.Enable()

    def OnBText6(self, event):
        dlg = wx.TextEntryDialog(self,
                                 message = "Enter a value the Template File",
                                 caption = "Configuration change",
                                 defaultValue = self.panelSText6.GetLabel(),
                                 )
        dlg.ShowModal()
        dlg.Destroy()
        value = dlg.GetValue()
        self.panelSText6.SetLabel(value)
        self.configData['threads'] = value
        self.panel_info.Layout()
        for each in self.configData:
            if self.configData[each] in ["''",'""','']: return
        self.serverButton.Enable()

    def OnLoad(self, event):
        dlg = wx.MessageDialog(self, "Coming Soon!", "Load File", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnReset(self, event):
        self.status = False
        self.inputFile = None
        
    def OnExit(self, event):
        dlg = wx.MessageDialog(self,
                               "Do you really want to close this application?",
                               "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            for thread in self.threads: thread.join()
            time.sleep(0.02)
            sys.exit()
##            self.Destroy()
        
    def OnLicense(self, event):
        dlg = wx.MessageDialog(self, "To view the license,\nsee license.txt", "License", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        
    def OnHelp(self, event):
        dlg = wx.MessageDialog(self, "To view Help,\nplease see Documentation.pdf", "Help", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnAbout(self, event):
        text = "APPRROD:\nA Python Program to Run Relap On Demeter\n\nCopyright (C) 2014\nAustin L Grelle\n\nA program to automate the\nvarious RELAP5-3D runs that\nneed to be ran based on\na given input set."
        dlg = wx.MessageDialog(self, text, "About APPRROD", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        
class logoPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.parent = parent
##        self.dc = Logo_Start
        self.Canvas = Logo_Start
        wx.EVT_LEFT_DOWN(self,self.OnLeftDown)

    def InitBuffer(self, CSCHEME = "White", items = []):
        self.size = self.GetClientSizeTuple()
        self.buffer = wx.EmptyBitmap(self.size[0],self.size[1])
        self.dc = wx.BufferedDC(wx.ClientDC(self),self.buffer)
        self.Canvas(self.dc,CSCHEME,
                    Size = (self.size[0],
                            self.size[1]),items = items)
        
    def OnPaint(self,event):
        """ The paint function to redraw the canvas
            based on the contents of the buffer
        """
        self.dc = wx.BufferedPaintDC(self,self.buffer)

    def OnLeftDown(self,event):
        """ When the left mouse button is clicked
        """
        self.thread.pause()

    def _startAnimation(self,):
        self.thread = panelThread(self,)
        self.parent.parent.threads.append(self.thread)
        self.thread.start()
        
def Logo_Start(dc,CSCHEME = "Black",
                  colorD = {},valueD = {},Size = (946,724),
                  texton = True, Position = (0,0), items = [[]]):
    if CSCHEME.lower() in ["white"]: CSCHEME2 = "Black"
    elif CSCHEME.lower() in ["black"]: CSCHEME2 = "White"
    else: CSCHEME2 = "Black"
    dc.SetBackground(wx.Brush(CSCHEME2,wx.SOLID))
    dc.Clear()
    dw,dh = (946,724)
    S = min((float(Size[1])/float(dh)),(float(Size[0])/float(dw)))
    Px, Py = Position
    dc.SetTextForeground(CSCHEME)
    if S > 1: P = S
    else: P = 1

    if S < 0.492 and S > 0.4755: SS = 0.47
    else: SS = S

    dc.SetBackground(wx.Brush(CSCHEME2,wx.SOLID))
    dc.Clear()
    pen = wx.Pen(CSCHEME,1,wx.SOLID)
    brush = wx.Brush(CSCHEME2,wx.SOLID)
    dc.SetPen(pen)
    dc.SetBrush(brush)
##    for item in items:
##        pen = wx.Pen("Grey",3,wx.SOLID)
##        dc.SetPen(pen)
##        dc.DrawLine(item[0][0],item[0][1],item[1][0],item[1][1])
    colorList = []
##    penList = []; penSize = 5;
    startValue = 255
    for j in range(len(items)):
        item = items[j]
        startValue = 255-(10*(len(items)-j))
        for i in range(len(item)):
            value = startValue-i*15
            if value < 0: value = 0
            colorList.append(wx.Colour(value, value, value))
    ##        penSize -= 0.1
    ##        if penSize < 1: penSize = 1
    ##        penList.append(penSize)
        for i in range(len(item)):
            pen = wx.Pen(colorList[-(i+1)],1,wx.SOLID)
            dc.SetPen(pen)
            dc.DrawLine(item[i][0][0],item[i][0][1],item[i][1][0],item[i][1][1])
    dc.SetFont(wx.Font(40,wx.SWISS,wx.ITALIC,wx.BOLD,underline=True))
    dc.DrawText("APPRROD",Size[0]/13*4,10)
    dc.SetTextForeground(CSCHEME2)
    dc.DrawText("APPRROD",Size[0]/13*4+4,6)
    dc.SetFont(wx.Font(11,wx.SWISS,wx.NORMAL,wx.NORMAL,underline=False))
    pen = wx.Pen(CSCHEME,15,wx.SOLID)
    dc.SetPen(pen)
    dc.SetTextForeground(CSCHEME2)
    dc.DrawLine(Size[0]/4,Size[1]-9,Size[0]-Size[0]/4+15,Size[1]-9)
    dc.DrawText("A Python Program to Run RELAP5-3D On Demeter",Size[0]/4,Size[1]-18)

class panelThread(threading.Thread):
    def __init__(self, parent,):
        super(panelThread, self).__init__()
        self.parent = parent
        self.stoprequest = threading.Event()
        self.pauserequest = threading.Event()
        self.items = [[]]
        self.counter = 20

    def run(self):
        while not self.stoprequest.isSet():
            if not self.pauserequest.isSet():
                self.stoprequest.wait(1./120)
                if not self.stoprequest.isSet(): self._process()
            else:
                self.stoprequest.wait(0.1)

    def join(self, timeout=None):
        self.stoprequest.set()
        super(panelThread, self).join(timeout)

    def pause(self,):
        if not self.pauserequest.isSet(): self.pauserequest.set()
        else: self.pauserequest.clear()

    def _process(self,):
##        t = random.random()
##        if t < 0.05:
            
        if len(self.items[-1]) < 15:
            if self.counter > 40:
                size = self.parent.GetClientSizeTuple()
                self.items[-1].append([[size[0],size[1]],[size[0] + 40,0]])
            else: self.counter += 1
        else:
            self.items.append([])
            self.counter = 0

        for j in range(len(self.items)):
            for i in range(len(self.items[j])):
                item = self.items[j][i]
                item[0][0] -= 1.0
                item[1][0] -= 0.5
                self.items[j][i] = item
        removeItems = []
        for i in range(len(self.items)):
            for j in range(len(self.items[i])):
                if self.items[i][j][0][0] <= -10 and self.items[i][j][1][0] <= -10: removeItems.append(i)
        removeItems.reverse()
        for thing in removeItems: self.items.pop(thing)
        self.parent.InitBuffer(items = self.items)
        
        
        
def PRA_Branching_Start(dc,CSCHEME = "White",
                  colorD = {},valueD = {},Size = (946,724),
                  texton = True, Position = (0,0)):
    if CSCHEME.lower() in ["white"]: CSCHEME2 = "Black"
    elif CSCHEME.lower() in ["black"]: CSCHEME2 = "White"
    else: CSCHEME2 = "Black"
    dc.SetBackground(wx.Brush(CSCHEME2,wx.SOLID))
    dc.Clear()
    dw,dh = (946,724)
    S = min((float(Size[1])/float(dh)),(float(Size[0])/float(dw)))
    Px, Py = Position
    dc.SetTextForeground(CSCHEME)
    if S > 1: P = S
    else: P = 1

    if S < 0.492 and S > 0.4755: SS = 0.47
    else: SS = S
    dc.SetFont(wx.Font(140*SS,wx.SWISS,wx.ITALIC,wx.BOLD,underline=True))
    dc.DrawText("APPRROD",20*S+Px,200*S+Py)
    dc.SetTextForeground(CSCHEME2)
    dc.DrawText("APPRROD",28*S+Px,192*S+Py)
    dc.SetFont(wx.Font(11*S,wx.SWISS,wx.NORMAL,wx.NORMAL,underline=False))
    dc.SetTextForeground(CSCHEME)
    dc.DrawText("A Python Program to Run RELAP5-3D On Demeter",300*S+Px,420*S+Py)
  
    if S != 1.0 and Position != [0,0]:
        dc.SetPen(wx.Pen(CSCHEME,5*S,wx.SOLID))
        dc.DrawLines(((Px,Py),(dw*S+Px+25,Py),(dw*S+Px+25,Py+dh*S),
                      (Px,Py+dh*S),(Px,Py)))

class drawFrame(wx.Frame):
    """ This frame will house the drawing panel.
    """
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1)
        self.parent = parent
        
        self.pp = (946,724)
        self.SetSize(self.pp)
        self.SetMinSize(self.pp)

        self.panel = drawPanel(self)
        self.inputFile = ''
        self.createMenuBar()

    def createMenuBar(self):
        
        # Create a menu bar with File, Data, and Help elements
        menuBar = wx.MenuBar()
        # File menu contains Station Identification, Program Restart, and Program Exit
        file_menu = wx.Menu()
        loadFile = file_menu.Append(wx.ID_ANY, "&Load Input File\tAlt-L", "Load Input File (Current = " + str(self.inputFile) + " )")
        menuReset = file_menu.Append(wx.ID_REVERT, "&Restart Program\tAlt-R", "Reset all Program values")
        menuExit = file_menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
        # Data menu contains Total Number of Colloquiums, Option to Load Student ID file,
        #    Option to Load Attendance File(s), and if both Student ID file and Attendance files
        #    have been loaded, then an option to run a report.
        data_menu = wx.Menu()
        option1 = data_menu.Append(wx.ID_ANY, "&Option 1", "Option 1")
        # Help menu contains options to show the License, Help, or About information
        help_menu = wx.Menu()
        menuLicense = help_menu.Append(wx.ID_ANY, "&License", "View License information for this program.")
        menuHelp = help_menu.Append(wx.ID_HELP_CONTENTS, "&Help", "View program Help file.")
        menuAbout= help_menu.Append(wx.ID_ABOUT, "&About"," View information about this program.")
        # Append the three menu items and set the menu bar
        menuBar.Append(file_menu, "&File")
        menuBar.Append(data_menu, "&Data")
        menuBar.Append(help_menu, "&Help")
        self.SetMenuBar(menuBar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.OnLoad, loadFile)
        self.Bind(wx.EVT_MENU, self.OnReset, menuReset)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        
        self.Bind(wx.EVT_MENU, self.OnLicense, menuLicense)
        self.Bind(wx.EVT_MENU, self.OnHelp, menuHelp)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        
        self.Bind(wx.EVT_CLOSE, self.OnExit)

    def OnLoad(self, event):
        dlg = wx.MessageDialog(self, "Coming Soon!", "Load File", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnReset(self, event):
        self.status = False
        self.inputFile = None
        
    def OnExit(self, event):
##        self.Destroy()
        sys.exit()
        
    def OnLicense(self, event):
        dlg = wx.MessageDialog(self, "To view the license,\nsee license.txt", "License", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        
    def OnHelp(self, event):
        dlg = wx.MessageDialog(self, "To view Help,\nplease see Documentation.pdf", "Help", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnAbout(self, event):
        text = "APPRROD:\nA Python Program to Run Relap On Demeter\n\nCopyright (C) 2014\nAustin L Grelle\n\nA program to automate the\nvarious RELAP5-3D runs that\nneed to be ran based on\na given input set."
        dlg = wx.MessageDialog(self, text, "About APPRROD", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        
class drawPanel(wx.Panel):
    """ This panel will draw the branching diagram.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.parent = parent
##        self.Bind(wx.EVT_IDLE, self.OnIdle)
        
        self.pp = (946,724)
        self.SetSize(self.pp)
        self.SetMinSize(self.pp)
        self.position = [0,0]
        self.Zoom = 1.0
        self.pos = [0,0]
        self.x, self.y = (0,0)
        self.xx, self.yy = (0,0)
        
        self.Canvas = PRA_Branching_Start
        
        self.CSCHEME = "White"
        self.SetBackgroundColour(self.CSCHEME)
##        if setup[0] == '1':
##            self.CSCHEME = "White"
##            self.SetBackgroundColour("Black")
##        else:
##            self.CSCHEME = "Black"
##            self.SetBackgroundColour("White")
        self.colorD = {}
        self.valueD = {}
        self.InitBuffer(self.CSCHEME)
            
##        self.InitBuffer(self.CSCHEME)
        wx.EVT_PAINT(self,self.OnPaint)
        wx.EVT_SIZE(self,self.OnSize)
        wx.EVT_MOUSEWHEEL(self,self.OnWheel)
        wx.EVT_MOTION(self,self.OnMotion)
        wx.EVT_LEFT_DOWN(self,self.OnLeftDown)
        
    def OnWheel(self,event):
        """ Controls what happens when the mouse wheel scrolls
        """
        v = event.GetWheelRotation()
        x,y = event.GetPosition()
        if self.x == x and self.y == y:
            if v > 0:
                if self.Zoom >= 3:
                    self.Zoom += 1
                    self.position[0] = self.position[0] - x
                    self.position[1] = self.position[1] - y
                elif self.Zoom >= 1:
                    self.Zoom += 0.25
                    self.position[0] = self.position[0] - x*0.25
                    self.position[1] = self.position[1] - y*0.25
                else:
                    self.Zoom += 0.1
                    self.position[0] = self.position[0] - x*0.1
                    self.position[1] = self.position[1] - y*0.1
            elif v < 0:
                if self.Zoom >= 3:
                    self.Zoom -= 1
                    self.position[0] = self.position[0] + x
                    self.position[1] = self.position[1] + y
                elif self.Zoom >= 1:
                    self.Zoom -= 0.25
                    self.position[0] = self.position[0] + x*0.25
                    self.position[1] = self.position[1] + y*0.25
                elif self.Zoom <= 0.1: self.Zoom = 0.1
                else:
                    self.Zoom -= 0.1
                    self.position[0] = self.position[0] + x*0.1
                    self.position[1] = self.position[1] + y*0.1
        else:
            self.xx, self.yy = (0,0)
            if v > 0:
                if self.Zoom >= 3:
                    self.Zoom += 1
                    self.xx = self.xx - x
                    self.yy = self.yy - y
                elif self.Zoom >= 1:
                    self.Zoom += 0.25
                    self.xx = self.xx - x*0.25
                    self.yy = self.yy - y*0.25
                else:
                    self.Zoom += 0.1
                    self.xx = self.xx - x*0.1
                    self.yy = self.yy - y*0.1
            elif v < 0:
                if self.Zoom >= 3:
                    self.Zoom -= 1
                    self.xx = self.xx + x
                    self.yy = self.yy + y
                elif self.Zoom >= 1:
                    self.Zoom -= 0.25
                    self.xx = self.xx + x*0.25
                    self.yy = self.yy + y*0.25
                elif self.Zoom <= 0.1: self.Zoom = 0.1
                else:
                    self.Zoom -= 0.1
                    self.xx = self.xx + x*0.1
                    self.yy = self.yy + y*0.1
            self.position[0] += self.xx
            self.position[1] += self.yy
        self.x, self.y = x,y
        self.OnSize(True)

    def OnLeftDown(self,event):
        """ When the left mouse button is clicked
        """
        self.pos = event.GetPosition()
        event.Skip()

    def OnMotion(self,event):
        """ When the mouse is moving across the canavas
        """
        if event.Dragging() and event.LeftIsDown():
            self.position[0] = self.position[0] + event.GetPosition()[0] - self.pos[0]
            self.position[1] = self.position[1] + event.GetPosition()[1] - self.pos[1]
            self.pos = event.GetPosition()
            self.OnSize(True)
        else:
            self.x, self.y = event.GetPosition()

    def InitBuffer(self, CSCHEME = "Black"):
        self.size = self.GetClientSizeTuple()
        self.buffer = wx.EmptyBitmap(self.size[0],self.size[1])
        dc = wx.BufferedDC(wx.ClientDC(self),self.buffer)
        self.Canvas(dc,CSCHEME,
                    Size = (self.size[0]*self.Zoom,
                            self.size[1]*self.Zoom),
                    Position = self.position,
                    colorD = self.colorD,
                    valueD = self.valueD)
        
    def OnPaint(self,event):
        """ The paint function to redraw the canvas
            based on the contents of the buffer
        """
        dc = wx.BufferedPaintDC(self,self.buffer)
        
    def OnSize(self,event):
        self.InitBuffer(self.CSCHEME)
        if self.Zoom > 1: g = self.Zoom
        else: g = 1
        if self.position[0] < -self.size[0]*g:
            self.position[0] = -self.size[0]*g
        elif self.position[0] > self.size[0]*g:
            self.position[0] = self.size[0]*g
        if self.position[1] < -self.size[1]*g:
            self.position[1] = -self.size[1]*g
        elif self.position[1] > self.size[1]*g:
            self.position[1] = self.size[1]*g

#-------------------------------------------------------------------
#---------------------------------------------------------------------
#-----------------------------------------------------------------------
#-------------------------------------------------------------------------
#---------------------------------------------------------------------------
#----------------------------------------------------------------------------
#                      _____________________________
#                     |           ______            |
#                     |          /\    /\           |
#                     |         /  \__/  \          |
#                     |        /   /  \   \         |
#                     |       /   /    \   \        |
#                     |      /   /      \   \       |
#                     |     /___/________\___\      |
#                     |     \  /          \  /      |
#                     |      \/____________\/       |
#                     |                             |
#                     | Argonne National Laboratory |
#                     |_____________________________|
#
#----------------------------------------------------------------------------
#---------------------------------------------------------------------------
#-------------------------------------------------------------------------
#-----------------------------------------------------------------------
#---------------------------------------------------------------------
#-------------------------------------------------------------------
