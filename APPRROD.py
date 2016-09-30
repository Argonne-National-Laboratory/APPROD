""" VERSION 0.8
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

File: APPRROD.py
______________________________________________________________________________
Total files:
  ->APPRROD.py
    APPRROD_GUI.py
    APPRROD_Lib.py
    APPRROD_Threads.py

Functions in this File:
    main()

Classes in this File:

"""
version = "0.8"
import sys, datetime, time
from APPRROD_Lib import *
from APPRROD_Threads import *
from APPRROD_GUI import *
import Tkinter, tkFileDialog
from multiprocessing import Manager
from multiprocessing.managers import SyncManager
import socket
import Queue

def main():
    """ Command-line version of APPRROD.
    """
    print("\nWelcome to APPRROD (v"+version+") Server Initialization!\n")
    
    # Make sure the program was started correctly
    assert '-c' in sys.argv or len(sys.argv) == 7 or '-h' in sys.argv, "Please provide all server options or use the '-c' option for using a config file. \n('-h' for information on server options)"

    # Print some help if the user asked for it
    if '-h' in sys.argv:
        print "\n" + "-"*50
        print "If the user wishes, they can specify server settings at the command line."
        print "However, they must specify all options in this case, and in the following order:"
        print "APPRROD.py [batFile] [licenseFile] [templateFile] [inputFile] [threads] [workingDirectory]"
        print ""
        print "Alternatively, a configuration file '.Config' can be used the '-c' option is provided\n"
        sys.exit()
        
    # Determine if there is a configFile
    if os.path.isfile(".Config"): configFile = ".Config"
    else:
        configFile = None
        if '-c' in sys.argv: print("-- No config file found. Starting with no options")

    # Assign appropriate values to data
    if configFile and '-c' in sys.argv:
        data, listItems = readConfigFile(configFile)
    elif '-c' in sys.argv and len(sys.argv) != 7:
        data = {'batFile': '',
                'licenseFile': '',
                'templateFile': '',
                'inputFile': '',
                'threads': '',
                'workingDirectory': '',
                'mode': 'server',
                'dist': False,
                'repository': '',
                'ip':'',
                'portnum':'',
                'authkey':''}
        listItems = data.keys()
    else:
        if '-c' in sys.argv: sys.argv = sys.argv.remove('-c')
        data = {'batFile': sys.argv[1],
                'licenseFile': sys.argv[2],
                'templateFile': sys.argv[3],
                'inputFile': sys.argv[4],
                'threads': sys.argv[5],
                'workingDirectory': sys.argv[6],
                'mode': sys.argv[7],
                'dist': (True if sys.argv[8].lower() in ['true','yes','y'] else False),
                'repository': sys.argv[9],
                'ip':sys.argv[10],
                'portnum':sys.argv[11],
                'authkey':sys.argv[12]}
        listItems = data.keys()

    # Print the current settings
    print("The settings are currently:\n")
    for each in listItems:
        print("_" + each + "_"*(40-len(each)) +"\n" + ' '*2 + ('None' if data[each] == "''" else str(data[each])))

    # Blocking loop that will prevent execution until the user specifies to start
    silent = False
    while True:

        if not silent:
            # Prompt the user for changes to these settings
            print("\nWould you like to change any options? (Y/N/Q) (Q: Quit)")
            while True:
                x = raw_input()
                if x.lower() in ['y','yes']:
                    print("\nPlease provide the category and the change to be made.")
                    print("Example: 'exe: helloWorld.exe'   for changing 'exe' value")
                    print("When finished, type 'x'\n")
                    while True:
                        x = raw_input()
                        if x.split(":")[0].strip().lower() in ['x']: break
                        elif ((len(x.split(":",1)) != 2) or
                              (x.split(":")[0].strip() not in data.keys() + ['x','X']) or
                              (not x.split(":",1)[1].isdigit() and x.split(":",1)[0].strip() == 'threads') or
                              (not os.path.isdir(x.split(":",1)[1].strip()) and x.split(":",1)[0] == 'workingDirectory') or
                              (not os.path.isfile(x.split(":",1)[1].strip()) and x.split(":",1)[0] in ['batFile','licenseFile','inputFile','templateFile',])):
                            print('Your input of : "' + x + '" does not confirm to the input structure.')
                            print("Please try again\n")
                        else:
                            data[x.split(":",1)[0].strip()] = x.split(":",1)[1].strip()
                    break
                elif x.lower() in ['n','no']: break
                elif x.lower() in ['q','quit']: return
                else:
                    print("Incorrect input, please try again:\n")

        silent = False
        print "\nAre you ready to start the server? (Y/N/P/Q) (P: Print Current Options)"
        x = raw_input()
        if x.lower() in ['y','yes']: break
        elif x.lower() in ['n','no']: pass
        elif x.lower() == 'q': return
        elif x.lower() == 'p':
            silent = True
            print("\nThe settings are currently:\n")
            for each in listItems:
                print("_" + each + "_"*(40-len(each)) +"\n" + ' '*2 + ('None' if data[each] == "''" else str(data[each])))
        else:
            silent = True
            print("Incorrect input, please try again:\n")            

    # Start the server and show the user the options
    print("\n --- Starting the " + data['mode'] + " with the following values ---\n")
    for each in listItems:
        print("_" + each + "_"*(40-len(each)) +"\n" + ' '*2 + ('None' if data[each] == "''" else str(data[each])))
    print("\n\n")
    if data['mode'] == 'server':
        if data['dist']:
            server = make_server_manager(port = data['portnum'], authkey = data['authkey'])
            manager = make_client_manager(ip = data['ip'], port = data['portnum'], authkey = data['authkey'])
        else: manager = False
        master = serverMasterThread(data, distributed = manager,)
        master.start()
    else:
        assert data['dist'], "If not the main server, MUST be a distributed configuration."
        server = None
        manager = make_client_manager(ip = data['ip'], port = data['portnum'], authkey = data['authkey'])
        master = serverMasterThread(data, distributed = manager,)

    print("APPRROD Started at " + str(datetime.datetime.now()) + "\n")
    print("Running until instructed to quit.")
    silent = False
    additionalRuns = []

    # In the main thread, block for raw input indicating to quit
    while True:

        try:

            if not silent:
                print "\n\n" + '_'*50
                print "What would you like to do?"
                print "  (i)       Print information about the running jobs and Queue lengths"
                print "  (t) [N]   Change the amount of worker threads to N threads"
                print "  (a)       Print the 'Advanced Options'"
                print "   - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
                print "  (o)       Read the .out files and print the total runs in each"
                print "            enumerated case."
                print "  (p)       Read the .p files and print the total runs in each"
                print "            enumerated case."
                print "   - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
                print "  (n)       Read in new input and template files, and add runs to the Queue"
                print "   - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
                print "  (q)       Quit\n"
            silent = False
            
            x = raw_input()
            
            if x.strip() == '': silent = True

            elif x.lower() == 'a':
                print "_"*18 + " Advanced Options" + "_"*18
                print "  (1)       Print the contents of the Out List"
                print "  (2)       Print the contents of the Job List"
                print "  (3)       Print the contents of the All Items List"
                print "  (s)       See if the 'cleanup' function is running."
                print "  (b)       List the configuration options that the server started with."
                print "  (c)       Check if all directories have the appropriate files."

            elif x.lower() == 'b':
                print("")
                for each in listItems:
                    print("_" + each + "_"*(40-len(each)) +"\n" + ' '*2 + ('None' if data[each] == "''" else str(data[each])))
                print("")

                if len(additionalRuns) > 0:
                    print "There were " + str(len(additionalRuns)) + " runs started since intialization:"
                    print '__________Template_File_(*.i)_____________________|_______Input_File(*.txt)____'
                    for each in additionalRuns:
                        print ' '*((51-len(each[0]))/2) + (' ' * ((51-len(each[0]))/2) + "|" + ' ' * ((31-len(each[1]))/2)).join(each)
                    print ""
            
            elif x.lower() == 'i':
                print "\nRunning threads  : " + str(master.queryRunning())
                print "\nJob Queue Length : " + str(master.sizeJQue())
                print "\nOut Queue Length : " + str(master.sizeOQue())
                
            elif x.lower().split()[0].strip() == 't':
                if len(x.lower().split()) > 2: print "Too many arguments for 't', try again."
                elif len(x.lower().split()) < 2:
                    N = master.numberOfThreads()
                    print "\nThere are currently " + str(N) + " worker threads."
                    print "Would you like to change the amount of worker threads? (y/n)"
                    while True:
                        y = raw_input()
                        if y.lower() == 'y':
                            
                            while True:
                                print "\nHow many worker threads would you like there to be?"
                                print "(Type 'c' to exit this prompt)\n"
                                y = raw_input()
                                if y.isdigit():
                                    change = int(y) - N
                                    if change == 0: print "\nNo change. returning to the main menu.\n"
                                    elif change < 0:
                                        master.killThreads(abs(change))
                                    elif change > 0:
                                        master.addThreads(change)
                                    else: print "There is some sort of error in the change threads code."

                                    print "\nThere are now " + str(master.numberOfThreads()) + " worker threads.\n"
                                    break
                                elif y.lower() == 'c': break
                                else:
                                    print "Incorrect input, please try again. (Type 'c' to exit this prompt)"
                            break
                        elif y.lower() == 'n': break
                        else:
                            print "Incorrect input, please try again."
                            
                else:
                    
                    if not x.lower().split()[1].strip().isdigit():
                        print "Incorrect argument to option 't', please try again.\n"
                        
                    else:
                        
                        N = master.numberOfThreads()
                        print "\nThere were " + str(N) + " worker threads."
                        change = int(x.lower().split()[1].strip()) - N
                        
                        if change == 0: print "\nNo change. returning to the main menu.\n"
                        elif change < 0:
                            master.killThreads(abs(change))
                        elif change > 0:
                            master.addThreads(change)
                        else: print "There is some sort of error in the change threads code."

                        print "\nThere are now " + str(master.numberOfThreads()) + " worker threads.\n"

            elif x.lower() == 'c1':
                stuff = []
                for each in master._outQ():
                    if each['Result'] != 0:
                        print each['Name'] + "'s run had result: " + each['Result']
                        print "Do you want to retry this run? (y/n)"
                        z = raw_input()
                        if z.lower() in ['y','yes']:
                            master.addJob({'Bat': each['Bat'],
                                           'Dir': each['Dir'],
                                           'Name': each['Name']})
                            stuff.append(each)
                        elif x.lower() in ['n','no']: continue
                        else: print "Incorrect input please try again."
                for each in stuff: master._outQ.remove(each)
                        
                
            elif x.lower() == 'c':
                stuffToRedo = checkFiles(data['workingDirectory'], jItems = master.jItems, dirList = master.allItems)
                
                print "It appears there are " + str(len(stuffToRedo)) + " Tasks that could be retried."
                print "Do you want to retry these tasks? (Y/N)"

                while True:
                    
                    y = raw_input()
                    
                    if y.lower() in ['y','yes']:
                        for each in stuffToRedo:
                            l = os.listdir(data['workingDirectory'] + os.sep + each)
                            i = ''
                            for item in l:
                                if item.endswith(".i"): i = item.split("\\")[-1].split(r'/')[-1].strip('.i')
                            if i == '': print "Problem with " + each
                            else:
                                newJob = {'Name': each,
                                          'Dir': data['workingDirectory'] + os.sep + each,
                                          'Bat': data['batFile']  + ' ' + i
                                          }
                                master.addJob(newJob)
                                master.stoprequest.wait(float(data['waitTime']))

                        print str(len(stuffToRedo)) + " new jobs added!\n"
                        break
                    elif y.lower() in ['n','no']: break
                    
                    else: print "Incorrect input, please try again!\n"
                
            elif x.lower() == 's':
                if master.finished.isSet(): print "** The master thread thinks we are finished. **"
                elif master.cleanprocess.isSet(): print "!! The cleanup process is running !!.\n"
                else: print "The cleanup process is not running.\n"
                
            elif x.lower() == 'o':
                stoppedFilesCases(data['workingDirectory'], o = True, dirList = master.allItems)
                
            elif x.lower() == 'p':
                stoppedFilesCases(data['workingDirectory'], p = True, dirList = master.allItems)

            elif x.lower() == 'n':

                print "\nDo you want to start new (n) runs or branch (b) from previous runs?"
                while True:
                    y = raw_input()
                    if y.lower() == 'n':                
                        # Get the new input filename
                        print "\nPlease select an input file (*.txt)"
                        fname = openFileDialog(title = 'Please select an input file.', fileTypes = [('Text file', '.txt'),('CSV file','.csv')])
                        if fname == '': print "\nNo file selected. No changes made."
                        
                        # If it was a file
                        else:
                            print "     You selected: " + fname + '\n'
                            newJobs = newRun(fname,data)
                            for each in newJobs:
                                master.addJob(each)
                                master.stoprequest.wait(master.waitTime)
                            print "\n" + str(len(newJobs)) + " Jobs started successfully!\n"
                        break
                    elif y.lower() == 'b':
                        while True:
                            print "\nDo you have a prepared Branching input deck? (y/n)"
                            y = raw_input()
                            if y.lower() in ['y','yes','n','no']:
                                wait = True
                                break
                            elif y.lower() in ['yb']:
                                wait = False
                                break
                            else: print "\nIncorrect input, please try again:"

                        if y.lower() in ['y','yes','yb']:                       
                            
                            # Get the new input filename
                            print "\nPlease select a Branching input deck file (*.txt)"
                            branchingName = openFileDialog(title = 'Please select a Branching input deck file.', fileTypes = [('.txt file', '.txt')])
                            if branchingName == '': print "\nNo file selected. No changes made."

                            q, runs, headB = branchRead(branchingName)
                            if q: break
                        
                        else:
                            runs = {}
                            headB = ['Simulation Scenario Name',
                                     'Sub-name',
                                     'Run #',
                                     'Template Location',
                                     'rstSTRIP Location',
                                     'varMap Location']
                            while True:
                                print "\nWhat is the previous simulation scenario name? (i.e. PLOF-SS):"
                                y = raw_input()
                                print "\nYou have entered " + y + ", is this correct? (y/n)"
                                z = raw_input()
                                
                                if z.lower() in ['y','yes']:
                                    runs['Simulation Scenario Name'] = y.strip()
                                    break
                                elif z.lower() in ['n','no']: continue
                                else: print "\nIncorrect input, please try again:"
                            while True:
                                print "\nWhat is the new sub-simulation scenario name? (i.e. PLOF-0PF):"
                                ys = raw_input()
                                print "\nYou have entered " + ys + ", is this correct? (y/n)"
                                z = raw_input()
                                if z.lower() in ['y','yes']:
                                    runs['Sub-name'] = ys.strip()
                                    break
                                elif z.lower() in ['n','no']: continue
                                else: print "\nIncorrect input, please try again:"
                            while True:
                                print "\nWhat is the range of numbers for scenario " + y
                                print "to copy?: (i.e. 1,10)"
                                z = raw_input()
                                if not (',' in z or ' ' in z): print "\nPlease enter two numbers separated by a ','."
                                elif len(z.split(',')) == 2:
                                    if z.split(",")[0].isdigit() and z.split(",")[1].isdigit():
                                        z1,z2 = z.split(',')
                                        z1 = int(z1); z2 = int(z2);
                                        runs['Run #'] = z
                                        break
                                    else: print "\nIncorrect input, please try again:"
                                elif len(z.split(' ')) == 2:
                                    if z.split(" ")[0].isdigit() and z.split(" ")[1].isdigit():
                                        z1, z2 = z.split(' ')
                                        z1 = int(z1); z2 = int(z2);
                                        runs['Run #'] = z
                                        break
                                    else: print "\nIncorrect input, please try again:"
                                else: print "\nIncorrect input, please try again:"

                            while True and runs == {}:
                                print "\nWill this run amend the template file with "
                                print "values from Rel3D_403-Xc_DQ.bat? (y/n)"
                                z = raw_input()
                                if z.lower() in ['y','yes','n','no']: break
                                else: print "\nIncorrect input, please try again:"
                            
                            # Get the new input filename
                            print "\nPlease select a template file (*.i)"
                            templateName = openFileDialog(title = 'Please select a template file.', fileTypes = [('.i file', '.i')])

                            if templateName == '': print "\nNo file selected. No changes made."
                            
                            print "     You selected: " + templateName + '\nCreating branch ' + templateName.strip('.i')
                            templateR = templateName.split('\\')[-1].split('/')[-1].strip('.i')
                            base = data['workingDirectory'] + os.sep + templateR

                            if z.lower() in ['y','yes']:

                                # Ask the user to locate the 'strip RST' .i file, then copy it
                                stripRST = openFileDialog(title = 'Please select the strip RST file.', fileTypes = [('.i file', '.i')])
                                if stripRST == '':
                                    print "\nNo file selected. Starting over."
                                    continue
                                runs['rstSTRIP Location'] = stripRST

                                # Ask the user to locate the 'variable mapping' file, then copy it
                                varMap = openFileDialog(title = 'Please select a variable map file.', fileTypes = [('.txt file', '.txt')])
                                if varMap == '':
                                    print "\nNo file selected. Starting over."
                                    continue
                                runs['varMap Location']
                        
                        branchJobs(runs,headB,data,master,wait)
                                    
                        os.chdir(data['workingDirectory'])   
                        break
                            
                    else: print "\nIncorrect input, please try again:"
                
            elif x == '1':
                # A 'hidden' option to look at the contents of the master's output queue
                out = master._outQ()
                print "---- length = " + str(len(out)) + "-----"
                print out

            elif x == '2':
                # A 'hidden' option to look at the running items.
                jobs = master._jobQ()
                print "---- length = " + str(len(jobs)) + "-----"
                print jobs  

            elif x == '3':
                # A 'hidden' option to look at all evaluated items
                items = master._allQ()
                print "---- length = " + str(len(items)) + "-----"
                print items          
                
            elif x.lower() == 'q':
                print("\nAre you sure you want to quit? (Y/N)\n")            
                x = raw_input()
                if x.lower() in ['y','yes']: break
                
            else:
                print "Incorrect input, please try again..."
                silent = True
                
        except Exception as e:
            print str(e) + " occured.\n"

##    print("\nSending quit signal to Server...")
    print("\nQuitting.\n")
    try:
        manager.join()
        if server: server.join()
    except: pass
    # Tell the thread to quit
    master.join()
    print("\nServer quit successfully!\n")
    sys.exit()

# If this script is ran as the "main" program    
if __name__ == '__main__':
    
    # For now, force the command-line option
    if '-c' not in sys.argv: sys.argv.append('-c')
    
    # Here is what we do if only the program was called,
    # i.e.: the GUI option
    if len(sys.argv) == 1 or '-gui' in sys.argv or '-GUI' in sys.argv:
        try: import wx
        except:
            print "\n\nThe GUI requires wxPython, please go to wxpython.org\n\n"
            sys.exit()
        app = wx.App(redirect=False)
        frame = mainFrame(None)
        frame.Show()
        app.SetTopWindow(frame)
        app.MainLoop()
        
    # Here is what we do if the program was called with
    # a few arguments, i.e.: the Command Line option
    else: main()

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
