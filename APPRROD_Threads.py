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

File: APPRROD_Threads.py
______________________________________________________________________________
Total files:
    APPRROD.py
    APPRROD_GUI.py
    APPRROD_Lib.py
  ->APPRROD_Threads.py

Functions in this File:

Classes in this File:
    serverMasterThread(d, N = 8, inputFileName = 'GenInput.txt', distributed = False,)
        Functions:
            get_IP(): return IP
            get_AUTHKEY(): return AUTHKEY
            get_PORTNUM(): return PORTNUM
            _readInputFile(fileName)
            _startJob(header, inputs, templateFile)
            startMoreJobs(header, inputs, templateFile)
            run()
            cleanprocessFunc()
            addJob(job)
            addThread()
            killThread()
            numberOfThreads()
            addThreads(N)
            killThreads(N)
            join(timeout=None)
            queryRunning()
            sizeJQue()
            sizeRQue()
            sizeOQue()
            _outQ()
            _jobQ()
            _allQ()
            _simulatorBrancher(out)
            addNewJobs(header, inputs, templateFile)
    serverThread(job_q, result_q, stoprequest = None, d = None)
        Functions:
            _startNewJob(header, inputs, templateFile)
            _branchNewJob(procDict,data)
            run()
            join(timeout=None)
            _process(procDict, passover = False)
            
"""

import os, threading, Queue, multiprocessing, subprocess, shutil, decimal, math, sys
import pickle
from APPRROD_Lib import *
from time import sleep

##from multiprocessing import managers
import socket

# Some important locations
homeDirectory = os.getcwd()

try:
    IP = socket.gethostbyname(socket.gethostname())
except socket.gaierror:
    IP = socket.gethostname()
except:
    IP = '0.0.0.0'
    
PORTNUM = 55444
AUTHKEY = 'relap'


class serverMasterThread(threading.Thread):
    """ The thread to initialize the 'sever' that will handle
        the creation, execution, and related tasks of threads.

        As an optional argument, takes an integer N amount of
        threads that it is allowed to create, which will also
        be equal to the amount of processes that it can create.
    """
    def __init__(self, d, N = 8, inputFileName = 'GenInput.txt', distributed = False,):
        super(serverMasterThread, self).__init__()
        self.d = d
        self.out = []
        self.distributed = distributed
        self.semaphore = threading.Semaphore(1)
        
        # If we provided a base directory to operate from,
        # set it, otherwise use C:\APPRROD
        if 'workingDirectory' in d: self.workingDirectory = d['workingDirectory']
        else:
            self.workingDirectory = r'C:\APPRROD'
            self.d['workingDirectory'] = self.workingDirectory
        
        # Store other things we may have provided, or assign
        # the variable to the default value if not
        if 'templateFile' in d: self.templateFile = d['templateFile']
        else: self.templateFile = 'ABR-1000-conv10.i'
        
        if 'batFile' in d: self.batFile = d['batFile']
        else: self.batFile = 'run_403.bat'
        
        if 'inputFile' in d: self.inputFileName = d['inputFile']
        else: self.inputFileName = inputFileName
        
        if 'taskName' in d: self.taskName = d['taskName']
        else: self.taskName = 'Task Number'
        
        if 'waitTime' in d: self.waitTime = float(d['waitTime'])
        else:
            self.waitTime = 0.1
            self.d['waitTime'] = '0.1'
        
        if 'repository' in d:
            if d['repository'] == d['workingDirectory']:
                self.repository = None
            else:
                self.repository = d['repository']
        else:
            self.repository = None

##        if distributed: assert os.path.isdir(self.repository), "No repository " + self.repository

        # ------ Thread stuff -------
        if distributed:
            self.manager = distributed
            self.job_q = self.manager.get_job_q()
            self.out_q = Queue.Queue()
            self.result_q = self.manager.get_result_q()
        else:
            self.job_q = Queue.Queue()
            self.out_q = Queue.Queue()
            self.result_q = None
        # If we have an input of threads from the function call,
        # set N to the value
        if 'threads' in self.d: N = int(self.d['threads'])
        # The event that will declare the thread should be killed
        self.stoprequest = threading.Event()
        self.waitrequest = threading.Event()

        # Create N threads and store their reference object in a list called threadingPool
        if self.job_q.qsize() > 0:
            self.threadPool = []
            for i in range(N):
                self.threadPool.append(serverThread(job_q = self.job_q, result_q = self.out_q,
                                                    d = (self.d if distributed else None),
                                                    semaphore = self.semaphore))
                self.stoprequest.wait(self.waitTime)
        else:
            self.threadPool = [serverThread(job_q = self.job_q,
                                            result_q = self.out_q,
                                            d = (self.d if distributed else None),
                                            semaphore = self.semaphore) for i in range(N)]

        # With the worker threads created, start their operation
        for thread in self.threadPool: thread.start()

        # A list to contain jobs in the that are being evaluated, and
        # a list to contain all items we have processed or will process
        self.jItems = []
        self.allItems = []
        
        # The thread event to declare if we've attempted to "clean up"
        self.cleanprocess = threading.Event()
        self.finished = threading.Event()

    def get_IP(self): return IP

    def get_AUTHKEY(self): return AUTHKEY

    def get_PORTNUM(self): return PORTNUM

    def _readInputFile(self, fileName):
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

    def _startJob(self, header, inputs, templateFile):
        """ Starts the first N jobs from the input file
        """

        # Create a local variable 'files' that is
        # a dictionary which will contain the mapping of
        # a file name to a string of its contentss
        files = {}

        # If we are working with the full path to the templateFile,
        # strip off the directories and get just the filename
        os.chdir(self.workingDirectory)
        
        # Load text-based files into local variables, rather than copying:
        for each in [templateFile, self.batFile]:

            # Try to open the file 100 times before giving up.
            i = 0
            j = False
            while i < 100:
                
                try:
                    # Operation to read in the files
                    f = open(each)                    
                    files[each] = f.read()
                    f.close()
                    i += 1
                    
                    j = True
                    break
                
                except Exception as e:
                    sleep(0.1)
                    
            if not j:
                print 'Unable to open: ' + str(each)
                    

        # For each entry in the input file
        for i in range(len(inputs[header[0]])):
            
            # Create a directory in the base's (but remove a previons run's progress if one exists)
            if os.path.isdir(self.workingDirectory + os.sep + inputs['Task Name'][i] + ' ' + inputs['Run#'][i]):
                shutil.rmtree(self.workingDirectory + os.sep + inputs['Task Name'][i] + ' ' + inputs['Run#'][i])

            self.stoprequest.wait(self.waitTime)

            os.mkdir(self.workingDirectory + os.sep + inputs['Task Name'][i] + ' ' + inputs['Run#'][i])
            
            # Copy the files over for the run.
            for each in [templateFile, self.batFile]:
                
                # Draw the elements from the files dictionary for each
                # file into a local string called 'localFile'
                localFile = files[each]
                
                # Open a new file for writing in the task's directory with the same name
                f = open(self.workingDirectory + os.sep + inputs['Task Name'][i] + ' ' + inputs['Run#'][i] + os.sep + each.split('\\')[-1].split('/')[-1],'w')

                # If we are operating on the input file.
                if each == templateFile:
                    
                    # For each variable stored in the header that is not
                    # the 'Task Name' or 'Run#'
                    for item in header[2:]:

                        print item

                        # Handle fixed input
                        if '$' in item:
                            
                            # Use a temporary file to write the results to
                            outFile = ''

                            # Name of the var in the file
                            name = "{" + item.split("$")[1].replace(".","") + "}"
                            print name

                            # Spacing before and after
                            spaceL = int(item.split("$")[0])
                            spaceR = int(item.split("$")[-1])
                            
                            # Iterate over each line in the localFile
                            for line in localFile.split("\n"):
                                
                                # If we found our term (minus the '.' character) in
                                # curly braces
                                if name in line:
                                    
                                    # Extract the value to the right of it
                                    value0 = line.split(name)[-1].split('}')[0].strip('{').strip()
                                    value = float(value0)
                                    # Replace the term and the following value with a multiplied value
                                    value = value * float(inputs[item][i])

                                    value = "{:.4E}".format(decimal.Decimal(value)).replace("E","e").replace("+","")
                                    
                                    line = line.replace("{" + name + "}" + "{" + str(value0) + "}", " "*spaceL + value + " "*spaceR)
                                    
                                    # Append the modified line to our temp outFile
                                    outFile += line + "\n"
                                    
                                else:
                                    # If the term isn't in it, just append the line
                                    outFile += line + "\n"
                                    
                            # Overwrite our localFile with the modified outFile
                            localFile = outFile

                        # The '.' character in a variable name
                        # indicates a multiplication operation
                        elif "." in item:
                            
                            # Use a temporary file to write the results to
                            outFile = ''
                            
                            # Iterate over each line in the localFile
                            for line in localFile.split("\n"):
                                
                                # If we found our term (minus the '.' character) in
                                # curly braces
                                if "{" + item.strip(".") + "}" in line:
                                    
                                    # Extract the value to the right of it
                                    value0 = line.split("{" + item.strip(".") + "}")[-1].split()[0].strip()
                                    value = float(value0)
                                    # Replace the term and the following value with a multiplied value
                                    value = value * float(inputs[item][i])
                                    # If the resulting multiplied value is longer than 9 characters,
                                    # convert it to Scientific Notation in the RELAP specified format
                                    if len(str(value)) > 9: value = "{:.4E}".format(decimal.Decimal(value)).replace("E","e").replace("+","")
                                    # ...Otherwise, typecast it as a string
                                    else: value = str(value)
                                    line = line.replace("{" + item.strip(".") + "}" + str(value0), value)
                                    
                                    # Append the modified line to our temp outFile
                                    outFile += line + "\n"
                                    
                                else:
                                    # If the term isn't in it, just append the line
                                    outFile += line + "\n"
                                    
                            # Overwrite our localFile with the modified outFile
                            localFile = outFile
                            
                        # Else, we are just substituting the label for a value from
                        # the inputs
                        else:
                            # Replace the occurance of {variable} with the value
                            # for the current case
                            localFile = localFile.replace('{' + item + '}',inputs[item][i])

                    # Now, write the changed localFile as the inputFile for this case
                    f.write(localFile)
                    
                # If we're not on the input file, just write the file string
                # to the new file
                else: f.write(files[each])

                # Close the current file we're operating on
                f.close()

        # With all of the folders created, spawn jobs
        for i in range(len(inputs[header[0]])):

            # Force the thread to wait for some time to try to prevent
            # the worker threads from accessing the .exe file at the same time
            if len(self.jItems) <= self.numberOfThreads(): self.stoprequest.wait(self.waitTime)
            
            # A newJob will have a bat command and a directory, for now
            newJob = {'Name': inputs['Task Name'][i] + ' ' + inputs['Run#'][i],
                      'Dir': self.workingDirectory + os.sep + inputs['Task Name'][i] + ' ' + inputs['Run#'][i] + os.sep,
                      'Bat': self.batFile + ' ' + templateFile.split('\\')[-1].split('/')[-1].strip('.i')
                      }

            # Put the new job in the job Queue
            self.addJob(newJob)

    def startMoreJobs(self, header, inputs, templateFile):
        """ Public API for adding new jobs, while the server is running.
            MUST provide valid header, inputs, and templateFile arguments
        """
                
        # Call the private _startFirstJob function with several optional arguments
        print "\nSetting up " + str(len(inputs[header[0]])) + " additional jobs beginning with " + inputs['Task Name'][0] + ' ' + inputs['Run#'][0]
        self._startJob(header = header, inputs = inputs, templateFile = templateFile)

    

    def run(self):
        """ Provide actions for the default run operation of the thread.
        """
        if self.d['mode'] == 'server':
            # As long as we weren't asked to stop, try to take new tasks from the
            # queue. The tasks are taken with a blocking 'get', so no CPU
            # cycles are wasted while waiting.
            # Also, 'get' is given a timeout, so stoprequest is always checked,
            # even if there's nothing in the queue.
            while not self.stoprequest.isSet():

                # Run the cleanprocess function
                if not self.distributed: self.cleanprocessFunc()

                try:
                    # Try and keep a connection
                    i = self.sizeJQue()
                    j = self.sizeRQue()
                    
                    # Blocks the thread until there is a result to 'get'
                    out = self.out_q.get(True,0.2)

                    # If we found something in the out queue, append
                    # it to our out list and remove it from our
                    # currently running jobs list
                    self.out.append(out)
                    self.jItems.remove(out['Name'])

                    # Result 47 is an abrupt stop due to something
                    # related to launching runs. Delete the files
                    # and re-add the run to the Queue
                    if out['Result'] in ['47',47]:
                        if os.path.isdir(out['Dir']):
                            fList = os.listdir(out['Dir'])
                            for f in fList:
                                if f.endswith('.out') or f.endswith('.p'):
                                    os.remove(out['Dir'] + os.sep + f)
                        newDict = {}
                        for each in out.keys():
                            if each != 'Result': newDict[each] = out[each]
                        self.addJob(newDict)
                    else:
                        self.result_q.put(out)
                    
                    # Runs the branching function
                    # (((TBD)))
                    
                # The above code will fail with a Queue.Empty error
                # if nothing is added in 0.2 seconds. If this is
                # the error, just continue to the next loop iteration.
                #
                # It is important that we block only for small amounts of
                # time and allow it to error with Queue.Empty so that
                # the thread doesn't lock up and prevent it from quitting
                # when requested, or other operations such as queryRunning, etc.
                except Queue.Empty:
                    continue
                except Exception as e:

                    # Errno 100 signifies the thread disconnected
                    if 'Errno 100' in str(e):
                        # Reconnect to the manager
                        self.manager = make_client_manager(ip = self.d['ip'],
                                                           port = self.d['portnum'],
                                                           authkey = self.d['authkey'])
                        self.stoprequest.wait(self.waitTime*2)
                        self.job_q = self.manager.get_job_q()
                        self.result_q = self.manager.get_result_q()
                        # Pass the job queue to all threads (Is this necessary?
                        #    Job threads reconnect on their own..)
                        for thread in self.threadPool: thread.job_q = self.job_q

                    # Print the error that occurred
                    print str(e) + " occurred in master thread."

                if self.d['mode'] == 'server':
                    try:
                        out = self.result_q.get(True,0.1)
                    except Queue.Empty:
                        continue
                    except Exception as e:
                        print str(e) + " occured in master thread."
                        
        elif self.d['mode'] == 'client':
            while not self.stoprequest.isSet():
                self.stoprequest.wait(self.waitTime)

    def cleanprocessFunc(self):
        """ A function to determine when it is time to
            clean up, and which Task #'s to attempt to run again.

            ((( DEPRECIATED )))
             - Current distributed implementation should not necessitate a clean function.
        """
        
        # Determine what items are remaining in all areas
        stuffLeft = self.queryRunning() + self.sizeJQue() + len(checkFiles(self.workingDirectory,
                                                                           self.jItems,
                                                                           self.allItems))

        # If there's nothing left, but we have yet to set the finished event, set it
        if stuffLeft == 0 and not self.finished.isSet():
            
            self.finished.set()

        # If there's still things do do, reset our cleanprocess event so we can do it again
        elif self.cleanprocess.isSet() and stuffLeft != 0 and not self.finished.isSet():
            
            self.cleanprocess.clear()
            self.stoprequest.wait(self.waitTime)

        # If the cleanprocess event isn't set and we have nothing in the job queue,
        # see if there are things we need to redo
        elif not self.cleanprocess.isSet() and not self.finished.isSet() and self.sizeJQue() == 0:

            # The function checkFiles will search for directories that don't
            # have the "correct" files in them
            stuffToRedo = checkFiles(self.workingDirectory, self.jItems, self.allItems)

            # For each item it identified as being a candidate for 'redoing'
            for each in stuffToRedo:
                # Check if the item is currently being evaluated
                if each not in self.jItems:
                    files = os.listdir(self.workingDirectory + os.sep + each)
                    tempFile = None
                    for f in files:
                        if f.endswith(".i"): tempFile = f.strip(".i")
                    if not tempFile: tempFile = self.templateFile.strip(".i")
                    # If it's not, create a new job for it and add
                    # it to the job queue
                    newJob = {'Name': each,
                              'Dir': self.workingDirectory + os.sep + each,
                              'Bat': self.batFile + ' ' + tempFile
                              }
                    self.addJob(newJob)
                # Artificially wait for a short amount of time
                self.stoprequest.wait(self.waitTime)

            # Set the clean process event
            self.cleanprocess.set()

    def addJob(self,job):
        """ If we need to add a job from an external function...
        """
        try:
            self.job_q.put(job)
            self.jItems.append(job['Name'])
            if job['Name'] not in self.allItems: self.allItems.append(job['Name'])
            self.finished.clear()
        except Exception as e:
            self.stoprequest.wait(0.5)
            if 'Errno 100' in str(e) or 'Errno 32' in str(e):
                self.manager = make_client_manager(ip = self.d['ip'],
                                                   port = self.d['portnum'],
                                                   authkey = self.d['authkey'])
                self.stoprequest.wait(self.waitTime*6)
                self.job_q = self.manager.get_job_q()
                self.addJob(job)
            else: print str(e)

    def addThread(self,):
        """ If we need to add a thread, create it and add it to our threadPool list
        """
        if self.distributed:
            thread = serverThread(job_q = self.job_q, result_q = self.out_q,
                                  stoprequest = self.stoprequest,
                                  d = self.d,
                                  semaphore = self.semaphore)
        else: thread = serverThread(job_q = self.job_q, result_q = self.out_q,
                                    stoprequest = self.stoprequest,
                                    semaphore = self.semaphore)
        thread.start()
        self.threadPool.append(thread)

    def killThread(self,):
        """ If we need to remove a thread, remove it from the
            threadPool list and tell it to join
        """
        thread = self.threadPool.pop()
        thread.join()

    def numberOfThreads(self,):
        """ A function to return the number of total threads
        """
        return len(self.threadPool)

    def addThreads(self, N):
        """ A function to add N threads
        """
        j = self.queryRunning()
        for i in range(N):
            self.addThread()
            j += 1
##            while self.queryRunning() < j:
##                self.waitrequest.wait(self.waitTime)

    def killThreads(self, N):
        """ A function to kill N threads
        """
        self.stoprequest.set()

        # Some counters for our progress bar
        l = N
        c = 1
        k = ['#' for item in range(75)]
        k = divideList(k,l)
        i = 0
        j = 0
        
        print "\nStopping " + str(N) + " threads..." + " "*(3-len(str(N))+51) + "|"
        print "_________________________________________________________________________V 100%"
        sys.stdout.write("|")
        
        for item in range(N):            

            # Display an elementary progress bar showing our progress
            if i*74//l > c:
                c = i*74//l
                sys.stdout.write(''.join(k[j]))
                j += 1
            i += 1
            
            self.killThread()

        print "\n"
        self.stoprequest.clear()
    
    def join(self, timeout=None):
        """ When the thread is called to "quit", here is how it will quit.
        """
        # Set the stop request, to tell it in other functions that we're done
        self.stoprequest.set()

        # Some counters for our progress bar
        l = len(self.threadPool)
        c = 1
        j = 0
        k = ['#' for item in range(75)]
        k = divideList(k,l)
        i = 0
        
        print "\nKilling " + str(l) + " threads..." + " "*(4-l) + "                                                   |"
        print "________________________________________________________________________V 100%"
        sys.stdout.write("|")
        
        # Then, we need to call the 'quit' function for each worker thread
        for proc in self.threadPool:            

            # Display an elementary progress bar showing our progress
            if i*74//l > c:
                c = i*74//l
                sys.stdout.write(''.join(k[j]))
                j += 1
            i += 1
            
            proc.join(timeout)
            
        print "\n"
        
        # Then, we will need to call the thread class's 'quit' operation
        # as well to handle any other quit things we didn't do in our
        # custom function
        super(serverMasterThread, self).join(timeout)

    def queryRunning(self,):
        """ A custom function to return the amount of running threads
        """
        # Initialize our counter
        j = 0
        
        # For each worker thread, check if it is running
        for proc in self.threadPool:
            # Our worker threads have a custom event called 'isrunning'
            # that is set while the .exe is running and turned off
            # when it is finished
            if proc.isrunning.isSet(): j += 1

        # Return the counter's result
        return j

    def sizeJQue(self,):
        """ A custom function to return the number of items
            in the job Queue
        """
        try:
            return self.job_q.qsize()
        except Exception as e:
            self.stoprequest.wait(0.5)
            if 'Errno 100' in str(e) or 'Errno 32' in str(e):
                self.manager = make_client_manager(ip = self.d['ip'],
                                                   port = self.d['portnum'],
                                                   authkey = self.d['authkey'])
                self.stoprequest.wait(self.waitTime*6)
                self.job_q = self.manager.get_job_q()
                return self.job_q.qsize()

    def sizeRQue(self,):
        try:
            return self.result_q.qsize()
        except Exception as e:
            self.stoprequest.wait(0.5)
            if 'Errno 100' in str(e) or 'Errno 32' in str(e):
                self.manager = make_client_manager(ip = self.d['ip'],
                                                   port = self.d['portnum'],
                                                   authkey = self.d['authkey'])
                self.stoprequest.wait(self.waitTime*6)
                self.result_q = self.manager.get_result_q()
                return self.result_q.qsize()

    def sizeOQue(self,):
        """ A custom function to return the number of items
            in the out Queue
        """
        return self.out_q.qsize()

    def _outQ(self,):
        """ A custom, hidden function to return the contents
            in the out Queue ###FOR TESTING PURPOSES###
        """
        return self.out

    def _jobQ(self,):
        """ A custom, hidden function to return the contents
            in the job items ###FOR TESTING PURPOSES###
        """
        return self.jItems

    def _allQ(self,):
        """ A custom, hidden function to return the contents
            of the all items list ###FOR TESTING PURPOSES###
        """
        return self.allItems

    def _simulatorBrancher(self, out):
        """ Takes as input the result and determines what jobs (if any)
            should be added to the jobs Queue
            #### TO BE ADDED LATER?? ####
        """

        # The simulator stopped successfully
        if out['Result'] == 0:
            reason = stoppedReason()

            # The simulator stopped because it reached a branching condition?
            if reason == 0:
                # Store the things we need to do in the list branches
                branches = []
                name = out['Name']
                args = out['Args']
                Dir  = out['Dir'].rsplit(os.sep,1)[0]
            
        # The simulator stopped for neither of the previous two reasons (abnormal termination)
        else: pass

    def addNewJobs(self, header, inputs, templateFile):
        # With all of the folders created, spawn jobs
        for i in range(len(inputs[header[0]])):

            # Force the thread to wait for some time to try to prevent
            # the worker threads from accessing the .exe file at the same time
            if len(self.jItems) <= self.numberOfThreads(): self.stoprequest.wait(self.waitTime)
            
            # A newJob will have a bat command and a directory, for now
            newJob = {'Name': inputs['Task Name'][i] + ' ' + inputs['Run#'][i],
                      'Dir': inputs['Task Name'][i] + ' ' + inputs['Run#'][i] + os.sep,
                      'Bat': self.batFile + ' ' + templateFile.split('\\')[-1].split('/')[-1].strip('.i'),
                      'header':header,
                      'inputs':[inputs[i]],
                      'templateName':templateFile,
                      'type':'new'
                      }

            # Put the new job in the job Queue
            self.addJob(newJob)


        
class serverThread(threading.Thread):
    """ A worker thread that takes job names from a queue,
        executes the job, waits for the result.

        Additionally, it also takes a result queue to store the
        result of the job, which should be used in the parent
        thread to assign more processes in the process queue if necessary.

        Input is done by placing processes (as dicts) into the
        Queue passed in job_q, where each process has keys for:
            - Name
            - Arguments
            - Directory for results
            - Exe location

        Output is done by placing tuples into the Queue passed in result_q.
        Each tuple is (process name, given arguments, result).

        Ask the thread to stop by calling its join() method.
    """
    def __init__(self, job_q, result_q, stoprequest = None, d = None, semaphore = None):
        super(serverThread, self).__init__()
        self.job_q = job_q
        self.result_q = result_q
        self.semaphore = semaphore
        if stoprequest: self.stoprequest = stoprequest
        else: self.stoprequest = threading.Event()
        self.isrunning = threading.Event()

        if d:
            assert os.path.isdir(d['repository']), "Cannot find the repository directory: " + str(d['repository'])
            self.repository = (None if d['repository'] == d['workingDirectory'] else d['repository'])
            self.workingDir = d['workingDirectory']
            self.workingDirectory = self.workingDir
            self.waitTime = float(d['waitTime'])
            self.batFile = d['batFile']
            self.d = d
        else: self.repository = None

    def _startNewJob(self, header, inputs, templateFile):
        """ copy files over
        """
        try:

            # Create a local variable 'files' that is
            # a dictionary which will contain the mapping of
            # a file name to a string of its contentss
            files = {}

            # If we are working with the full path to the templateFile,
            # strip off the directories and get just the filename
            os.chdir(self.workingDirectory)
            
            baseDir = homeDirectory
            
            # Load text-based files into local variables, rather than copying:
            for each in [templateFile, self.batFile]:
                i = 0
                j = False
                while i < 100:
                    
                    try:
                        if each == templateFile:
                            f = open(each)
                        elif each == self.batFile:
                            f = open(baseDir + os.sep + each.split('\\')[-1].split('/')[-1])
                        else:
                            f = open(each)
                        files[each] = f.read()
                        f.close()
                        j = True
                        break
                        
                    except:
                        sleep(0.1)
                        i += 1

                if not j:
                    print 'Unable to open: ' + str(each)
                        
                
            # Create a directory in the base's
            os.mkdir(self.workingDirectory + os.sep + inputs['Task Name'] + ' ' + inputs['Run#'])
            
            # Copy the files over for the run.
            for each in [templateFile, self.batFile]:
                
                # Draw the elements from the files dictionary for each
                # file into a local string called 'localFile'
                localFile = files[each]
                
                # Open a new file for writing in the task's directory with the same name
                f = open(self.workingDirectory + os.sep + inputs['Task Name'] + ' ' + inputs['Run#'] + os.sep + each.split(os.sep)[-1].split('\\')[-1].split('/')[-1],'w')

                # If we are operating on the input file.
                if each == templateFile:
                    
                    # For each variable stored in the header that is not
                    # the 'Task Name' or 'Run#'
                    for item in header[2:]:

                        # Handle fixed input
                        if '$' in item:
                            
                            # Use a temporary file to write the results to
                            outFile = ''

                            # Name of the var in the file
                            name = "{" + item.split("$")[1].replace(".","") + "}"

                            # Spacing before and after
                            spaceL = int(item.split("$")[0])
                            spaceR = int(item.split("$")[-1])
                            
                            # Iterate over each line in the localFile
                            for line in localFile.split("\n"):
                                
                                # If we found our term (minus the '.' character) in
                                # curly braces
                                if name in line:

                                    while name in line:
                                    
                                        # Extract the value to the right of it
                                        value0 = line.split(name)[-1].split('}')[0].strip('{').strip()
                                        value = float(value0)
                                        # Replace the term and the following value with a multiplied value
                                        value = value * float(inputs[item])

                                        value = "{:.4E}".format(decimal.Decimal(value)).replace("E","e").replace("+","")
                                        
                                        line = line.replace(name + "{" + str(value0) + "}", " "*spaceL + value + " "*spaceR)
                                    
                                    # Append the modified line to our temp outFile
                                    outFile += line + "\n"
                                    
                                else:
                                    # If the term isn't in it, just append the line
                                    outFile += line + "\n"
                                    
                            # Overwrite our localFile with the modified outFile
                            localFile = outFile

                        # The '.' character in a variable name
                        # indicates a multiplication operation
                        elif "." in item:
                            
                            # Use a temporary file to write the results to
                            outFile = ''
                            
                            # Iterate over each line in the localFile
                            for line in localFile.split("\n"):
                                
                                # If we found our term (minus the '.' character) in
                                # curly braces
                                if "{" + item.strip(".") + "}" in line:
                                    
                                    # Extract the value to the right of it
                                    value0 = line.split("{" + item.strip(".") + "}")[-1].split()[0].strip()
                                    value = float(value0)
                                    # Replace the term and the following value with a multiplied value
                                    value = value * float(inputs[item])
                                    # If the resulting multiplied value is longer than 9 characters,
                                    # convert it to Scientific Notation in the RELAP specified format
                                    if len(str(value)) > 9: value = "{:.4E}".format(decimal.Decimal(value)).replace("E","e").replace("+","")
                                    # ...Otherwise, typecast it as a string
                                    else: value = str(value)
                                    line = line.replace("{" + item.strip(".") + "}" + str(value0), value)
                                    
                                    # Append the modified line to our temp outFile
                                    outFile += line + "\n"
                                    
                                else:
                                    # If the term isn't in it, just append the line
                                    outFile += line + "\n"
                                    
                            # Overwrite our localFile with the modified outFile
                            localFile = outFile
                            
                        # Else, we are just substituting the label for a value from
                        # the inputs
                        else:
                            # Replace the occurance of {variable} with the value
                            # for the current case
                            localFile = localFile.replace('{' + item + '}',inputs[item])

                    # Now, write the changed localFile as the inputFile for this case
                    f.write(localFile)
                    
                # If we're not on the input file, just write the file string
                # to the new file
                else: f.write(files[each])

                # Close the current file we're operating on
                f.close()
                
                if each == self.batFile and 'linux' in sys.platform:
                        os.system('chmod +x "' + self.workingDirectory + os.sep + inputs['Task Name'] + ' ' + inputs['Run#'] + os.sep + each.split(os.sep)[-1].split('\\')[-1].split('/')[-1] + '"')
        except Exception as e:
            print "\n" + str(e) + " error in thread.\n"
            os.chdir(self.workingDirectory)

    def _branchNewJob(self,procDict,data):

        try:            
            base = data['workingDirectory'] + os.sep + procDict['templateR']
            if not os.path.isdir(base): os.mkdir(base)
            
            y = procDict['Simulation Scenario Name']
            ys = procDict['Sub-name']
            stripRST = procDict['stripRST']
            varMap = procDict['varMap']
            i = procDict['i']

            if os.path.isdir(base + os.sep + ys + ' ' + str(i)):
                shutil.rmtree(base + os.sep + ys + ' ' + str(i))

            self.isrunning.wait(self.waitTime)

            try: os.mkdir(base + os.sep + ys + ' ' + str(i))
            except WindowsError as e:
                print "\nError : " + str(e)
                print "\nThe directory already exists. Please delete the directory"
                print "if you would like to launch a run with these settings.\n"
##                stopping = True
##                break
                return 1
            
            # Copy files
            fCheck = 0
            while fCheck < 100 and not any([each.endswith(procDict['templateR'] + '.r') for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                self.isrunning.wait(self.waitTime)
                fCheck += 1
                
                f = open(self.repository + os.sep + procDict['rFile'],'rb')
                f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + procDict['templateR'] + '.r','wb')
                f2.write(f.read()); f.close(); f2.close();
                
            fCheck = 0
            while fCheck < 100 and not any([each.endswith(procDict['templateR'] + '.plt') for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                self.isrunning.wait(self.waitTime)
                fCheck += 1
            
                f = open(self.repository + os.sep + procDict['pltFile'],'rb')
                f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + procDict['templateR'] + '.plt','wb')
                f2.write(f.read()); f.close(); f2.close();
                
            fCheck = 0
            while fCheck < 100 and not any([each.endswith(data['batFile'].split(os.sep)[-1].split('\\')[-1].split('/')[-1]) for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                self.isrunning.wait(self.waitTime)
                fCheck += 1
            
                f = open(self.batFile, 'rb')
                f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + data['batFile'].split(os.sep)[-1].split('\\')[-1].split('/')[-1],'wb')
                f2.write(f.read()); f.close(); f2.close();
            
            # Template file might need to be modified
            if stripRST and varMap:
                # If the template file needs to be modified...
                
                #Copying convert_all_403ie.exe
                fCheck = 0
                while fCheck < 100 and not any([each.endswith('convert_all_403ie.exe') for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                    self.isrunning.wait(self.waitTime)
                    fCheck += 1
                    f = open(data['workingDirectory'] + os.sep + 'Files For Restart' + os.sep + 'convert_all_403ie.exe','rb')
                    f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + 'convert_all_403ie.exe','wb')
                    f2.write(f.read()); f.close(); f2.close();
                    
                fCheck = 0
                while fCheck < 100 and not any([each.endswith('Rel3D_403-Xc_DQ.bat') for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                    self.isrunning.wait(self.waitTime)
                    fCheck += 1
                        
                    # Copying Rel3D_403-Xc_DQ.bat
                    f = open(data['workingDirectory'] + os.sep + 'Files For Restart' + os.sep + 'Rel3D_403-Xc_DQ.bat','rb')
                    f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + 'Rel3D_403-Xc_DQ.bat','wb')
                    f2.write(f.read()); f.close(); f2.close();
                    
                fCheck = 0
                while fCheck < 100 and not any([each.endswith(stripRST.split('\\')[-1].split('/')[-1]) for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                    self.isrunning.wait(self.waitTime)
                    fCheck += 1
                
                    f = open(stripRST, 'rb')
                    f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + stripRST.split('\\')[-1].split('/')[-1],'wb')
                    f2.write(f.read()); f.close(); f2.close();
                    
                fCheck = 0
                while fCheck < 100 and not any([each.endswith(varMap.split('\\')[-1].split('/')[-1]) for each in os.listdir(base + os.sep + ys + ' ' + str(i))]):

                    self.isrunning.wait(self.waitTime)
                    fCheck += 1
                
                    f = open(varMap, 'rb')
                    f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + varMap.split('\\')[-1].split('/')[-1],'wb')
                    f2.write(f.read()); f.close(); f2.close();

                # With all of the necessary files called, invoke the .bat file
                FNULL = open(os.devnull, 'w')
                os.chdir(base + os.sep + ys + ' ' + str(i))
                status = subprocess.call('Rel3D_403-Xc_DQ.bat ' + stripRST.split('\\')[-1].split('/')[-1].strip('.i') + ' ' + procDict['templateR'],
                                         stdout=FNULL, stderr=subprocess.STDOUT)

                # Now, list all of the files in the directory
                fList = os.listdir(base + os.sep + ys + ' ' + str(i) + os.sep)
                # Find the file that ends in .Excel
                for f in fList:
                    if f.endswith('.Excel'): break
                assert f.endswith('.Excel')
                    
                # Open the file that ends in .Excel
                contents = open(base + os.sep + ys + ' ' + str(i) + os.sep + f)
                # Read from contents into d
                for line in contents:
                    if line.startswith('  plotalf'): headLabel = line.strip()
                    elif line.startswith('  plotnum'): headNum = line.strip()
                    elif line != '': finalLine = line
                
                # Close this .Excel file
                contents.close()
                
                # Open the variable mapping text file
                f = open(varMap)
                dOut = {}
                for line in f:
                    # If there's an asterisk in the first character, assume
                    # its a comment
                    if line[0] == '*': continue
                    # Split the line
                    varName, rName, rNum = line.strip().split()
                    # Read the value from the .Excel file determination step
                    dOut[varName] = str(finalLine.split()[headNum.split().index(rNum)])

                f.close()

                # Now, open the template file
                f = open(procDict['templateFile'])
                # Get the contents
                contents = f.read()
                # Close the file
                f.close()
                # Replace each item with its value
                for item in dOut: contents = contents.replace('{' + item + '}', str(dOut[item]))
                # Create a new file in the new directory with the template name
                f = open(base + os.sep + ys + ' ' + str(i) + os.sep + procDict['templateR'] + '.i','w')
                # Write contents to it
                f.write(contents)
                # Close it
                f.close()
                
            # Template file isn't modified
            else: 
                f = open(self.repository + os.sep + procDict['templateFile'], 'rb')
                f2 = open(base + os.sep + ys + ' ' + str(i) + os.sep + procDict['templateR'] + '.i','wb')                                
                f2.write(f.read()); f.close(); f2.close();
    
        except Exception as e:
            print "\n" + str(e) + " error in Branching thread method.\n"
            os.chdir(self.workingDirectory)        

    def run(self):
        """ Provide actions for the default run operation of the thread.
        """
        
        # As long as we weren't asked to stop, try to take new tasks from the
        # queue. The tasks are taken with a blocking 'get', so no CPU
        # cycles are wasted while waiting.
        #
        # Also, 'get' is given a timeout, so stoprequest is always checked,
        # even if there's nothing in the queue.
        while not self.stoprequest.isSet():
            
            try:
                # Block until the timeout or we get a job from the job queue
                procDict = self.job_q.get(True, 0.05)

                # If we got a job, process the job and get the result
                procDict['Result'] = self._process(procDict)

                # Put the result in the result queue
                self.result_q.put(procDict)

            # The above code will fail with a Queue.Empty error
            # if nothing is added in 0.05 seconds. If this is
            # the error, just continue to the next loop iteration.
            #
            # It is important that we block only for small amounts of
            # time and allow it to error with Queue.Empty so that
            # the thread doesn't lock up and prevent it from quitting
            # when requested
            except Queue.Empty:
                continue
            except Exception as e:
                print "\n" + str(e) + " error in thread Main Process on line + " + str(sys.exc_info()[2].tb_lineno) + "\n"
                self.stoprequest.wait(0.5)
                if 'Errno 100' in str(e) or 'Errno 32' in str(e):
                    self.manager = make_client_manager(ip = self.d['ip'],
                                                       port = self.d['portnum'],
                                                       authkey = self.d['authkey'])
                    self.stoprequest.wait(self.waitTime*6)
                    self.job_q = self.manager.get_job_q()
                os.chdir(self.workingDirectory)
        
        # Then, we will need to call the thread class's 'quit' operation
        # as well to handle any other quit things we didn't do in our
        # custom function
        super(serverThread, self).join(timeout)

    def join(self, timeout=None):
        """ When the thread is called to "quit", here is how it will quit.
        """
        # Set the stop request, to tell it in other functions that we're done
        self.stoprequest.set()

    def _process(self, procDict, passover = False):
        """ Given a process dictionary, calls the simulator exe
        """
        # Wait to begin
        self.semaphore.acquire()

        if not passover:
            if procDict['type'] == 'new':
                self._startNewJob(procDict['header'],procDict['inputs'],procDict['templateName'])
            elif procDict['type'] == 'branch':
                r = self._branchNewJob(procDict,self.d)
                if r == 2: return 2
        
        # Change directory to the prescribed directory
        while True:
            try:
                if procDict['type'] == 'new':
                    print "New run: " + self.workingDir + os.sep + procDict['Dir'].rstrip('\\').rstrip('/')
                    os.chdir(self.workingDir + os.sep + procDict['Dir'].rstrip('\\').rstrip('/'))
                    break
                elif procDict['type'] == 'branch':
                    print "Branched " + procDict['Dir'].rstrip('\\').rstrip('/')
                    os.chdir(self.workingDir + os.sep + procDict['Dir'].rstrip('\\').rstrip('/'))
                    break
                    
            except Exception as e:
                print e
                self.isrunning.wait(self.waitTime)
                continue

        # Set the 'isrunning' event to indicate we are processing
        # the request
        self.isrunning.set()

        # Open a pipe to dump output to from the batch file operation so it
        # doesn't fill the screen
        if 'win' in sys.platform: 
            FNULL = open(os.devnull, 'w')
        else:
            FNULL = open(os.devnull, 'w')

        # Release the semaphore
        sleep(self.waitTime)
        
        # Run the command and record the resulting status of the command
        if 'win' in sys.platform:         
            self.semaphore.release()
            status = os.system(procDict['Bat'] + " > NUL")
        elif 'linux' in sys.platform:
            self.semaphore.release()
            status = os.system('.' + os.sep + self.batFile.split(os.sep)[-1].split('\\')[-1].split('/')[-1] + ' ' + procDict['Bat'].split()[-1])
        else:
            self.semaphore.release()
            status = os.system(procDict['Bat'])

        sleep(self.waitTime)

        # We're now finished running at this point, so clear the 'isrunning' event
        self.isrunning.clear()

        if self.repository and status not in [47,'47',1,'1',2]:

            try: 
                # Remove the P file if it is 'Transient terminated by end of time step cards.' in '.out'
                if procDict['type'] == 'new':                
                    location = self.repository + os.sep + procDict['Dir'].strip(os.sep).strip('\\').strip('/')
                    locationUsed = self.workingDir + os.sep + procDict['Dir'].rstrip('\\').rstrip('/')
                elif procDict['type'] == 'branch':
                    location = self.repository + os.sep + procDict['Dir'].strip(os.sep).strip('\\').strip('/')
                    locationUsed = self.workingDir + os.sep + procDict['Dir'].rstrip('\\').rstrip('/')
                    
                if os.path.isdir(location):
                    print "The directory already exists at the repository location:\n" + location
                    return 144

                # Remove the P file if it is 'Transient terminated by end of time step cards.' in '.out'             
                #x = removeP(locationUsed)

                # For RELAP case where for some reason we didn't start.
                # TODO: this shouldn't happen. Need to figure out why it happens.   
                # Wait to begin
                self.semaphore.acquire()          
                if False:#isinstance(x,str):
                    if '.p perhaps file already exists.' in x:
                        for f in os.listdir(locationUsed):
                            os.remove(locationUsed + os.sep + f)
                        shutil.rmtree(locationUsed, onerror=remove_readonly)
                        print "p file already existed, trying again for " + procDict['Dir'].strip(os.sep).strip('\\').strip('/')
                        return self._process(procDict)
                
                else:
                    shutil.copytree(locationUsed,location)
                    sleep(self.waitTime*2)
                    while True:
                        try:
                            shutil.rmtree(locationUsed, onerror=remove_readonly)
                            break
                        except Exception as e:
                            sleep(self.waitTime)
                            if 'Error 32' in str(e): continue
                            else:
                                print str(e)
                                break
                self.semaphore.release()   
            except Exception as e:
                print str(e) + " on line + " + str(sys.exc_info()[2].tb_lineno)
                raise 
            
        elif status in [47,'47']:
            sleep(self.waitTime)
            fList = os.listdir(d + os.sep + procDict['Dir'])
            for f in fList:
                if f.endswith('.out') or f.endswith('.p'):
                    os.remove(d + os.sep + procDict['Dir'] + os.sep + f)
            self._process(procDict,passover=True)
        
        # Return the result: 0 if no problems
        return status

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
