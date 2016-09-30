import os

def removePs(d = "C:\APPRROD\Runs", deleteFiles = False):
    l = os.listdir(d)
    fileTotal = 0

    for i in range(len(l)):
            if os.path.isdir(d + os.sep + l[i]):
                    for j in range(len(os.listdir(d + os.sep + l[i]))):
                            if os.path.isdir(d + os.sep + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j]):
                                    files = os.listdir(d + os.sep + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j])
                                    yes = False
                                    for f in files:
                                            if f.endswith('.out'):
                                                    fContents = open(d + os.sep + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j] + os.sep + f)

                                                    # Store the last part of the file in 'finalLine'                        
                                                    try:
                                                        # Change the file pointer to near the end of the file
                                                        fContents.seek(-300,os.SEEK_END)
                                                        # Read from this near point to the end of the file
                                                        finalLine = fContents.read(abs(-300))
                                                        
                                                    # If we get an IOError, then it probably means
                                                    # we can't seek [endFileCriteria] characters back from
                                                    # the end, and we can assume the the file has less
                                                    # than [endFileCriteria] characters and we can read the
                                                    # entire file into memory.
                                                    except IOError:
                                                            fContents.close()
                                                            fContents = open(d + os.sep + f)
                                                            finalLine = fContents.read()

                                                    if 'Transient terminated by end of time step cards.' in finalLine:
                                                            yes = True
                                                            break
                                    if yes:
                                            for f in files:
                                                    if f.endswith(".p"):
                                                            print "We deleted " + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j] + os.sep + f
                                                            fileTotal += os.stat(d + os.sep + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j] + os.sep + f).st_size
                                                            if deleteFiles: os.remove(d + os.sep + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j] + os.sep + f)
                                    else: print "Nothing to do for " + l[i] + os.sep + os.listdir(d + os.sep + l[i])[j]
            else: print d + os.sep + l[i] + " is apparently not a directory"
                                    
    return fileTotal


##if __name__ == '__main__': removePs(d = os.getcwd(), deleteFiles = False)
