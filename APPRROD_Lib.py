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

File: APPRROD_Lib.py
______________________________________________________________________________
Total files:
    APPRROD.py
    APPRROD_GUI.py
  ->APPRROD_Lib.py
    APPRROD_Threads.py

Functions in this File:
    get_j_q()
    get_r_q()
    make_server_manager(port, authkey)
    make_client_manager(ip, port, authkey)
    divideList(l,n)
    loadFileDialog(message = "Please select a file.")
    openFileDialog(title = 'Please select an input file.', fileTypes = [('Text file', '.txt')])
    saveFileAsDialog(message = "Please select a file.")
    readConfigFile(fname)
    stoppedFilesCases(directory, o = False, p = False, dirList = None)
    stoppedFilesCheck(directory, o = False, p = False, dirList = None)
    readInputFile(fileName)
    newRun(fname, data)
    branchRead(branchingName)
    branchJobs(runs,headB,data,master, wait = True)
    checkFiles(directory, jItems = [], dirList = None)

Classes in this File:

"""

import os, wx, threading, Queue, multiprocessing, subprocess, time, shutil, decimal, math, sys
import Tkinter, tkFileDialog
import pickle
import socket

from multiprocessing import Manager
from multiprocessing.managers import SyncManager

# Server --------------------------
class JobQueueManager(SyncManager):
    pass

job_q = multiprocessing.Queue()

def get_j_q(): 
    return job_q

result_q = multiprocessing.Queue()

def get_r_q():
    return result_q

import multiprocessing.reduction

def make_server_manager(port, authkey):
    """ Create a manager for the server, listening on the given port.
        Return a manager object with get_job_q and get_result_q methods.
    """

    # This is based on the examples in the official docs of multiprocessing.
    # get_{job|result}_q return synchronized proxies for the actual Queue
    # objects.

    JobQueueManager.register('get_job_q', callable=get_j_q)
    JobQueueManager.register('get_result_q', callable=get_r_q)
    manager = JobQueueManager(address=('', int(port)), authkey=authkey)
    manager.start()
    print 'Server started at port %s' % port
    return manager

# Client --------------------------
class ServerQueueManager(SyncManager):
    pass

def make_client_manager(ip, port, authkey):
    """ Create a manager for a client. This manager connects to a server on the
        given address and exposes the get_job_q and get_result_q methods for
        accessing the shared queues from the server.
        Return a manager object.
    """

    ServerQueueManager.register('get_job_q')
    ServerQueueManager.register('get_result_q')

    manager = ServerQueueManager(address=(ip, int(port)), authkey=authkey)
    manager.connect()

    print 'Client connected to %s:%s' % (ip, port)
    return manager

# Functions --------------------------

def divideList(l,n):
    o = [0 for i in range(n)]
    q = 0
    while q < len(l):
        for j in range(n):
            o[j] += 1; q += 1;
            if q == len(l): break
    p = [l[:o[0]]]
    for i in range(1,len(o)): p.append(l[sum(o[:i]):sum(o[:i])+o[i]])
    return p

def loadFileDialog(message = "Please select a file."):
    dlg = wx.FileDialog(self,
                        message = message,
                        defaultDir = homeDirectory,
                        defaultFile = "",
                        wildcard = "Text Files (*.txt)|*.txt",
                        style = wx.OPEN)
    dlg.ShowModal()
    dlg.Destroy()

def openFileDialog(title = 'Please select an input file.', fileTypes = [('Text file', '.txt')]):
    root = Tkinter.Tk()
    root.withdraw()
    options = {}
    options['filetypes'] = fileTypes
    options['title'] = title
    output_file = tkFileDialog.askopenfilename(**options)
##    if output_file == '':
##        print "No file selected, exiting..."
##        raw_input()
##        sys.exit()
    return output_file

def saveFileAsDialog(message = "Please select a file."):
    dlg = wx.FileDialog(self,
                        message = "Select or Create Save File",
                        defaultDir = homeDirectory,
                        defaultFile = "",
                        wildcard = "Text Files (*.txt)|*.txt",
                        style = wx.SAVE)
    dlg.ShowModal()
    dlg.Destroy()    

def readConfigFile(fname):
    """ A function designed to read the input file '.Config' which
        contains information delimited by the '=' character.
    """
    d = {}
    f = open(fname)
    things = ['exe','args','inputFile',
              'threads','batFile',
              'licenseFile','templateFile',
              'workingDirectory','taskName','waitTime',
              'mode','dist','repository',
              'ip','portnum','authkey']
    listThings = []
    for line in f:
        thing = line.strip().split("=")[0].strip()
        if thing == 'dist':
            d[thing] = (True if line.strip().split("=")[1].strip() in ['true','yes','y'] else False)
            listThings.append(thing)
        elif thing in things:
            d[thing] = line.strip().split("=")[1].strip()
            listThings.append(thing)
    f.close()
    return d, listThings

def stoppedFilesCases(directory, o = False, p = False, dirList = None):
    """ A function to sum the different possible output results
        and print these results to the user.
    """
    
    # Default cases we will check for
    defaultCases = ['Transient terminated by end of time step cards.',
                    'Transient terminated by trip.',
                    'RELAP5-3D: Errors detected during input processing.',
                    'Thermodynamic property error with minimum time step, transient being terminated.'
                    ]
    
    # A dictionary to store results in 
    stoppingCases = {}
    stillRunning = []
    
    # Create a dictionary mapping for each default case
    for case in defaultCases:
        stoppingCases[case] = {'count':0,
                               'files':[]}
        
    # The amount of characters we will look for at the end of the file
    endFileCriteria = -300 #characters
    # (Thermodynamic case has roughly 295 characters for full description)

    # If we have a directory list rather than just looking for 'Task' in
    # the directory name....
    if dirList: files = dirList
    else: files = os.listdir(directory)
    i = 0

    if not o and not p: fType = ".out"
    elif o: fType = ".out"
    elif p: fType = ".p"
    else: print "\nWe have an error with the file type extension.\n\n"
    
    for each in files:
        
        if os.path.isdir(directory + os.sep + each): d = directory + os.sep + each
        elif os.path.isdir(each): d = each
        else: d = None
        
        if d:
            if 'Task' in each or dirList:
                # Counter for how many cases we have
                i += 1

                # Files in the case's directory
                dir_files = os.listdir(d)
                for f in dir_files:

                    # Right now, let's check the .out file still
                    if f.endswith(fType):
                        # Open the file
                        fContents = open(d + os.sep + f)

                        # Store the last part of the file in 'finalLine'                        
                        try:
                            # Change the file pointer to near the end of the file
                            fContents.seek(endFileCriteria,os.SEEK_END)
                            # Read from this near point to the end of the file
                            finalLine = fContents.read(abs(endFileCriteria))
                            
                        # If we get an IOError, then it probably means
                        # we can't seek [endFileCriteria] characters back from
                        # the end, and we can assume the the file has less
                        # than [endFileCriteria] characters and we can read the
                        # entire file into memory.
                        except IOError:
                            fContents.close()
                            fContents = open(d + os.sep + f)
                            finalLine = fContents.read()
                            
                        # A local 'flag' to tell us if we found something or not
                        foundOne = False
                        
                        if fType == '.out':
                            if ' ' in finalLine.split("\n")[-2]:
                                if len(finalLine.split("\n")[-2].split()) == 6:
                                    stillRunning.append(each)
                                    
                        if each not in stillRunning:

                            # For each of our known cases
                            for case in stoppingCases:
                                # If we found the case
                                if case in finalLine:
                                    # Increment our counter for the case
                                    stoppingCases[case]['count'] += 1
                                    # Record which file this happened in
                                    stoppingCases[case]['files'].append(each)
                                    # Set our local 'flag' to true showing we found it
                                    foundOne = True
                                    # We don't need to search anymore
                                    break
                            
                        # If we didn't identify a case we already knew,
                        # then let's add a new case for what was there
                        if not foundOne and each not in stillRunning:
                            stoppingCases[finalLine] = {'count':1,'files':[each]}

                        # Close the file
                        fContents.close()

    # Print the results to the screen
    print "\n__The finished " + str(i) + " cases shown in configuration (b) resulted in:___\n"
    print "Cases currently running: " + str(len(stillRunning)) + "\n"

    # Maintain output order 
    outList = []
    for case in defaultCases + stoppingCases.keys():
        if case not in outList: outList.append(case)
        
    newCase = False
    # For each case
    for case in outList:
        # The length of the text describing the case will
        # determine whether or not we must add spaces after it
        # or concatenate the output (by printing "..." at the
        # beginning of the line's item)
        n = len(case)
        ddd = 'o '
        if n > 60:
            n = len(case) - 60
            ddd = '  -'#ddd = '...'
        # If we are on the portion of printing output where
        # we have a new case, then distinguish it by a line
        # labeled "NEW ERRORS", but only print it once
        if case not in defaultCases and not newCase:
            newCase = True
            print "\n" + "_"*30 + " NEW ERRORS " + "_"*30

        # For every case, print the case and the count of items for that case
        # to the screen in an organized fashion
        print "\n"
        if len(case) > 60: print "o " + case.strip()[:60] + '-'
        print ddd + case.strip()[-n:] + " "*(66-n-len(ddd)) + ":" + str(stoppingCases[case]['count'])

        # If the case is not one of the default cases, print each of the directories
        # which had the case
        if case not in defaultCases: print stoppingCases[case]['files']
    print "\n"

def stoppedFilesCheck(directory, o = False, p = False, dirList = None):
    """ A function to sum the different possible output results
        and print these results to the user.
    """
    
    # Default cases we will check for
    defaultCases = ['Transient terminated by end of time step cards.',
                    'Transient terminated by trip.',
                    'RELAP5-3D: Errors detected during input processing.',
                    'Thermodynamic property error with minimum time step, transient being terminated.'
                    ]
    
    # A dictionary to store results in 
    stoppingCases = {}
    stillRunning = []
    
    # Create a dictionary mapping for each default case
    for case in defaultCases:
        stoppingCases[case] = {'count':0,
                               'files':[]}
        
    # The amount of characters we will look for at the end of the file
    endFileCriteria = -300 #characters
    # (Thermodynamic case has roughly 295 characters for full description)

    # If we have a directory list rather than just looking for 'Task' in
    # the directory name....
    if dirList: files = dirList
    else: files = os.listdir(directory)
    i = 0

    if not o and not p: fType = ".out"
    elif o: fType = ".out"
    elif p: fType = ".p"
    else: print "\nWe have an error with the file type extension.\n\n"
    
    for each in files:
        
        if os.path.isdir(directory + os.sep + each):
            d = stoppedFilesCheck(directory + os.sep + each, o = o, p = p)
            for each in d:
                stoppingCases[each]['count'] += d[each]['count']
                stoppingCases[each]['files'] += d[each]['files']
        else:
            # Right now, let's check the .out file still
            if each.endswith(fType):
                # Open the file
                fContents = open(directory + os.sep + each)

                # Store the last part of the file in 'finalLine'                        
                try:
                    # Change the file pointer to near the end of the file
                    fContents.seek(endFileCriteria,os.SEEK_END)
                    # Read from this near point to the end of the file
                    finalLine = fContents.read(abs(endFileCriteria))
                    
                # If we get an IOError, then it probably means
                # we can't seek [endFileCriteria] characters back from
                # the end, and we can assume the the file has less
                # than [endFileCriteria] characters and we can read the
                # entire file into memory.
                except IOError:
                    fContents.close()
                    fContents = open(directory + os.sep + f)
                    finalLine = fContents.read()
                    
                # A local 'flag' to tell us if we found something or not
                foundOne = False
                
                if fType == '.out':
                    if ' ' in finalLine.split("\n")[-2]:
                        if len(finalLine.split("\n")[-2].split()) == 6:
                            stillRunning.append(each)
                            
                if each not in stillRunning:

                    # For each of our known cases
                    for case in stoppingCases:
                        # If we found the case
                        if case in finalLine:
                            # Increment our counter for the case
                            stoppingCases[case]['count'] += 1
                            # Record which file this happened in
                            stoppingCases[case]['files'].append(directory)
                            # Set our local 'flag' to true showing we found it
                            foundOne = True
                            # We don't need to search anymore
                            break
                    
                # If we didn't identify a case we already knew,
                # then let's add a new case for what was there
                if not foundOne and each not in stillRunning:
                    stoppingCases[finalLine] = {'count':1,'files':[each]}

                # Close the file
                fContents.close()

    # Print the results to the screen
    return stoppingCases

def readInputFile(fileName):
    """ Reads in the 'input' file to get the task names, run numbers,
        and 'variable' values for the templateFile

        return header, inputs
    """
    entryTypes = []
    validFile = False
    try:
        
        # Read in our input file
        f = open(fileName)
        fContents = f.read(); f.close();
        if '\n' not in fContents: f = fContents.replace('\r','\n')
        f = fContents.split("\n")
        
        # Store the variables we will change from the
        # first line in a class variable called 'header'
        header = []
        
        # Store the values for each test case in the
        # input file in a class variable called 'inputs'
        # that is a dictionary mapping the "header's"
        # variable to a list of all entries from the file
        inputs = {}
        
        # Now, for the first line, read it and split
        # it based on commas
        for each in f[0].split(","):
            # Append the variable to the header list
            header.append(each.strip())
            # Add an entry in the inputs dictionary
            # for the header variable and map it to an empty list
            inputs[each.strip()] = []

        # Now for each remaining line in the file
        for each in f[1:]:
            # The items in the line are separated by commas
            line = each.split(",")
            
            # For each variable in the header
            for i in range(len(header)):
                # Append the line's item at index 'i' to the header's
                # list at index 'i'
                inputs[header[i]].append(line[i].strip())

                # Stuff to check if the entry Input Deck has correct value types
                # for each case

                # If we're on the first row, record what type the values should be
                if len(entryTypes) == i:
                    if "." in line[i].strip(): entryTypes.append(float)
                    elif line[i].strip()[0].isdigit(): entryTypes.append(int)
                    else: entryTypes.append(str)
                else:
                    lType = None
                    if "." in line[i].strip(): lType = float
                    elif line[i].strip()[0].isdigit(): lType = int
                    else: lType = str
                    if lType != entryTypes[i]:
                        print "On line " + str(len(inputs['Task Name'])+1) + " the value of " + str(line[i].strip())
                        print "is of type " + str(lType) + ", but function expects " + str(entryTypes[i])
                        print "----- Should we halt the input? (Y/N)"
                        while True:
                            x = raw_input()
                            if x.lower() in ['y', 'yes']: return [],[]
                            elif x.lower() in ['n','no']: break
                            else: print "Incorrect input.. please try again.\n"
        
        validFile = True
            
    except Exception as e:
        print "\nThere was an error loading your input file: " + str(e)
        print "No changes have been made."
        return [],[]

    if 'Task Name' not in inputs or 'Run#' not in inputs:
        print 'The input file must contain entries for "Task Name" and "Run#".'
        print 'No action taken.\n'
        return [],[]
    
    # First, check and see if each of job and number represent
    # available folders
    probs = []
    for i in range(len(inputs['Task Name'])):
        if os.path.isdir(inputs['Task Name'][i] + ' ' + inputs['Run#'][i]):
            probs.append(inputs['Task Name'][i] + ' ' + inputs['Run#'][i])

    if len(probs) > 0:
        print "\nThe following directories conflict with your"
        print "selected input file " + fileName + ":"
        for each in probs: print each
        print "\n"
        return [],[]

    return header, inputs

def newRun(fname, data):
    
    # Get the new input filename
    print "\nPlease select a template file (*.i)"
    templateName = openFileDialog(title = 'Please select a template file.', fileTypes = [('.i file', '.i')])
    if templateName == '': print "\nNo file selected. No changes made."
    
    # If the template file was a valid file
    else:
        print "     You selected: " + templateName + '\n'
        header, inputs = readInputFile(fname)

        if header != [] and inputs != []:
##            additionalRuns.append([templateName.split('\\')[-1].split('/')[-1].strip(".i"),
##                                   fname.split('\\')[-1].split('/')[-1].strip(".txt")])
            newJobs = []
            for i in range(len(inputs['Task Name'])):
                newInputs = {}
                for each in header: newInputs[each] = inputs[each][i]
                newJobs.append({'Name':templateName.split('\\')[-1].split('/')[-1].strip(".i"),
                                'type':'new',
                                'Dir':data['workingDirectory'] + os.sep + inputs['Task Name'][i] + ' ' + inputs['Run#'][i] + os.sep,
                                'Bat':data['batFile'] + ' ' + templateName.split('\\')[-1].split('/')[-1].strip('.i'),
                                'header': header,
                                'inputs': newInputs,
                                'templateName': templateName
                                })
            print newJobs
            return newJobs

def branchRead(branchingName):
    fB = open(branchingName)
    sep = ''
    items = ['Simulation Scenario Name',
             'Sub-name',
             'Run #',
             'Template Location',
             'rstSTRIP Location',
             'varMap Location']
    runs = {}; headB = [];
    q = False
    for line in fB:
        if sep == '':
            if ';' in line: sep = ';'
            elif '\t' in line: sep = '\t'
            else:
                print "Please use either a semicolon (;) or tab character"
                print "in the branching input deck file."
                q = True
                break
        if 'Simulation Scenario Name' in line:
            if len(line.split(sep)) == 6:
                for each in line.split(sep):
                    runs[each.strip()] = []
                    headB.append(each.strip())
                for each in items:
                    if each not in runs:
                        print each + " not found in the header."
                        print "Please include this column, even if blank."
                        q = True
                        break
            else:
                print "Please have all six categories in the "
                print "branching input deck file."
                for each in items:
                    print " - " + each
                q = True
                break
        else:
            if 'Simulation Scenario Name' not in runs:
                for each in items:
                    runs[each] = []
                    headB.append(each)
            lineContents = line.split(sep)
            assert len(lineContents) == len(headB), '"The line with ' + str(lineContents) + ' has too many tab characters."'
            for i in range(len(lineContents)):
                runs[headB[i]].append(lineContents[i].strip())
    return q, runs, headB

def branchJobs(runs,headB,data,master, wait = True):
    
    for ij in range(len(runs[headB[0]])):
        templateR = runs['Template Location'][ij].split('\\')[-1].split('/')[-1].strip('.i')
        base = data['workingDirectory'] + os.sep + templateR
    
##        if not os.path.isdir(base): os.mkdir(base)

        stripRST = runs['rstSTRIP Location'][ij]
        varMap = runs['varMap Location'][ij]
        
        z1,z2 = runs['Run #'][ij].split(',')
        z1 = int(z1); z2 = int(z2);

        y = runs['Simulation Scenario Name'][ij]
        ys = runs['Sub-name'][ij]

        stopping = False
        
        for i in range(z1,z2+1):
                
            name = y + ' ' + str(i)
            
            files = os.listdir(data['repository'] + os.sep + name)
            
            for each in files:
                if each.endswith('.r'): rFile = each
                elif each.endswith('.plt'): pltFile = each
##            try: os.mkdir(base + os.sep + ys + ' ' + str(i))
##            except WindowsError as e:
##                print "\nError : " + str(e)
##                print "\nThe directory already exists. Please delete the directory"
##                print "if you would like to launch a run with these settings.\n"
##                stopping = True
##                break
            
            newJob = {'Name': base + os.sep + ys + ' ' + str(i),
                      'type': 'branch',
                      'Dir': base + os.sep + ys + ' ' + str(i),
                      'Bat': data['batFile'] + ' ' + templateR,
                      'templateR': templateR,
                      'Simulation Scenario Name':y,
                      'Sub-name':ys,
                      'i':i,
                      'rFile':data['repository'] + os.sep + y + ' ' + str(i) + os.sep + rFile,
                      'templateFile':runs['Template Location'][ij],
                      'pltFile':data['repository'] + os.sep + y + ' ' + str(i) + os.sep + pltFile,
                      'batFile':data['workingDirectory'] + os.sep + data['batFile'],
                      'licenseFile':data['workingDirectory'] + os.sep + data['licenseFile'],
                      'convertallFile':data['workingDirectory'] + os.sep + 'Files For Restart' + os.sep + 'convert_all_403ie.exe',
                      'rel3dFile':data['workingDirectory'] + os.sep + 'Files For Restart' + os.sep + 'Rel3D_403-Xc_DQ.bat',
                      'stripRST':stripRST,
                      'varMap':varMap}

            # Add the job
            master.addJob(newJob)  

            # Force the thread to wait for some time to try to prevent
            # the worker threads from accessing the .exe file at the same time
            if wait: time.sleep(master.waitTime)

        if stopping: break

def checkFiles(directory, jItems = [], dirList = None):
    stuffToRedo = []
    goodThings = []
    biggerProblems = []    

    # If we have a directory list rather than just looking for 'Task' in
    # the directory name....
    if dirList: files = dirList
    else: files = os.listdir(directory)
    
    # For each item in the overall directory
    for each in files:
        
        # Check if it is a directory
        if os.path.isdir(directory + os.sep + each):
            
            # If so, check if 'Task' is in the name
            if ('Task' in each or dirList) and each not in jItems:
                
                # If so, get the files and directories in this directory
                dir_Files = os.listdir(directory + os.sep + each)
                
                # A flag that will tell us if the '.out' file is
                # in this directory, or the '.p' file
                outInHere = False
                pInHere = False

                # Now for each file/directory in the directory
                for every in dir_Files:
                    # If it ends with .out, then set our flag to True
                    if every.endswith(".out"): outInHere = True
                    # If it ends with .p, then set our flag to True
                    if every.endswith(".p"): pInHere = True

                # If we found an .out file
                if outInHere or pInHere:
                    # If there are seven files, let's say it is a good run
                    if len(dir_Files) == 7: goodThings.append(each)
                    # Otherwise, we have a bigger problem
                    else: biggerProblems.append(each)
                    
                # If we only have three files, we have merely copied over
                # the files and have not executed a run
                elif len(dir_Files) == 3: stuffToRedo.append(each)
                
                # If there was no .out file, and we have other files, then
                # we have a bigger problem
                else: biggerProblems.append(each)

    return stuffToRedo
