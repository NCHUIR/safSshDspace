import sys,os,re,json,time
import paramiko
from stat import S_ISDIR,S_ISREG

# =========================
# testing ...
# =========================

def loadJsonConfig(jsonPath):
    jsonFile=open(jsonPath)
    data = json.load(jsonFile)
    jsonFile.close()
    return data

def execute(client, command, sudoPW=False):
    if sudoPW:
        command = "sudo -S -p '' %s" % command
    stdin, stdout, stderr = client.exec_command(command)
    if sudoPW:
        stdin.write(sudoPW + "\n")
        stdin.flush()
    return {'out': stdout.readlines(), 
            'err': stderr.readlines(),
            'retval': stdout.channel.recv_exit_status()}

def testSSH():

    sshConfig = loadJsonConfig('setting.json')
    print(sshConfig)

    print("testing ssh...")
    # Testing ssh...
    client = paramiko.client.SSHClient()
    client.load_system_host_keys()
    client.connect(
        hostname = sshConfig['hostname'],
        username = sshConfig['username'],
        password = sshConfig['password'],
    )
    print("client.exec_command ...\n")

    command = "wget http://docs.paramiko.org/en/1.13/api/sftp.html"
    command = "dmesg"
    # stdin, stdout, stderr = channel.exec_command(command)

    print("ssh_test:\n",execute(client,command,sshConfig['password']))

    print("exec_command test done!")

    # client needs to start from Transport obj
    sftp = client.open_sftp()
    print("\nsftp listdir in root:\n",sftp.listdir("/"))

    client.close()

# =========================
# testing end
# =========================

class safSshDspace:

    def __init__(self,setting):

        # default setting:
        self.setting = {
            'hostname':'',
            'username':'',
            'password':'',

            'SAFTmpDir':'',

            'requireRoot':False,
            'dspaceBin':'',
            'mapfileDir':'',
            'DspaceIdentity':'',

            'command-name':'import',
            'action':'add',
            'toResume':False,

            'action_flags':{
                'add':'-a',
                'replace':'-r',
                'delete':'-d',
            },
            'flags':{
                'source':'-s',
                'eperson':'-e',
                'collection':'-c',
                'mapfile':'-m',
                'resume':'-R',
                'unknown':'-q',
            },

            'SAFContains':['dublin_core.xml'],
            'commandTimeout':60,
            'localMapFileName':'mapfile',
            'keepOriMapFile':{
                'local':True,
                'remote':False,
            },
            'keepUploadedSAF':False,
        }

        self.setting.update(setting)
        self.client = None
        self.sftp = None

    def connect(self):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.connect(
            hostname = self.setting['hostname'],
            username = self.setting['username'],
            password = self.setting['password'],
        )
        self.client = client
        sftp = client.open_sftp()
        self.sftp = sftp

    def isSAFItem(self,dirpath):
        if not os.path.isdir(dirpath):
            return False

        result = True
        listdir = os.listdir(dirpath)

        for f in self.setting['SAFContains']:
            result = result and (f in listdir)

        return result

    def genSAFList(self,dirpath): # generate SAF list
        if not os.path.isdir(dirpath):
            return []

        # is collection level
        isCollLevel = False

        SAFCollList = []

        for item in os.listdir(dirpath):
            isCollLevel =  self.isSAFItem(os.path.join(dirpath,item))
            if not isCollLevel:
                break;

        if isCollLevel:
            SAFCollList.append(dirpath)
            return SAFCollList
        else:
            for item in os.listdir(dirpath):
                SAFCollList += self.genSAFList(os.path.join(dirpath,item))
            return SAFCollList

    @staticmethod
    def verbose(level,content = ""):
        if level is 0:
            return
        elif level is 1:
            sys.stdout.write('.')
        else:
            print(content)

    @staticmethod
    def put_r(sftp,localpath,remotepath,verboseLevel = 1): # recursively upload a full directory
        result = []
        localpath = os.path.abspath(localpath)
        localpathLen = len(os.path.split(localpath)[0])
        for walker in os.walk(localpath):
            r_path = os.path.join(remotepath,walker[0][localpathLen+1:])
            try:
                sftp.mkdir(r_path)
                __class__.verbose(verboseLevel,"sftp.mkdir: [%s]" % r_path)
                result.append(r_path)
            except:
                pass
            for f in walker[2]:
                lf_path = os.path.join(walker[0],f)
                rf_path = os.path.join(r_path,f)
                sftp.put(lf_path,rf_path)
                __class__.verbose(verboseLevel,"sftp.put [%s] => [%s]" % (lf_path,rf_path))
                result.append([lf_path,rf_path])
        if verboseLevel is 1:
            print("")
        return result

    @staticmethod
    def remove_r(sftp,remotepath,verboseLevel = 0): # recursively remove a full directory
        removed = []
        if S_ISDIR(sftp.stat(remotepath).st_mode):
            for f in sftp.listdir_attr(remotepath):
                fpath = os.path.join(remotepath,f.filename)
                if S_ISDIR(f.st_mode):
                    removed += __class__.remove_r(sftp,fpath)
                else:
                    sftp.remove(fpath)
                    removed.append(fpath)
                    __class__.verbose(verboseLevel,"sftp.remove: [%s]" % fpath)
            sftp.rmdir(remotepath)
            removed.append(remotepath)
            __class__.verbose(verboseLevel,"sftp.rmdir: [%s]" % remotepath)
        else:
            sftp.remove(remotepath)
            removed.append(remotepath)
            __class__.verbose(verboseLevel,"sftp.remove: [%s]" % remotepath)
        if verboseLevel is 1:
            print("")
        return removed

    def toFS(self,safCollPath): # scp to file system
        if not self.sftp:
            raise Exception("Not connected yet!")
        sftp = self.sftp

        SAFColl = os.path.split(os.path.abspath(safCollPath))[1]
        src_path = safCollPath
        
        SAFTmpDir = self.setting['SAFTmpDir']
        des_path = os.path.join(SAFTmpDir,SAFColl)

        if SAFColl in sftp.listdir(SAFTmpDir):
            #return des_path
            print("SAFColl: [%s] exists! Removing [%s]..." % (SAFColl,des_path))
            __class__.remove_r(sftp,des_path)

        print("uploading from [%s] into [%s]..." % (src_path,SAFTmpDir))
        __class__.put_r(sftp,src_path,SAFTmpDir)

        return des_path

    def mapFilePath(self,SAFColl):
        if not self.sftp:
            raise Exception("Not connected yet!")
        sftp = self.sftp
        mapFilePath = os.path.join(self.setting['mapfileDir'],SAFColl)

        try:
            sftp.mkdir(self.setting['mapfileDir'])
        except Exception as e:
            try:
                exists = S_ISREG(sftp.stat(mapFilePath).st_mode)
            except Exception as e:
                exists = False
            
            if exists and not self.setting['toResume']:
                print("mapfile exists! removing...")
                sftp.remove(mapFilePath)

        return mapFilePath

    @staticmethod
    def execute(client, command, sudoPW = False, timeout = 60):
        if sudoPW:
            command = "sudo -S -p '' %s" % command
        print("command: [%s]" % command)
        stdin, stdout, stderr = client.exec_command(command)
        if sudoPW:
            stdin.write(sudoPW + "\n")
            stdin.flush()
        return {'out': stdout.readlines(), 
                'err': stderr.readlines(),
                'retval': stdout.channel.recv_exit_status()}

    # ===============================
    # dspaceImportCMD example:
    # ===============================
    # 
    # normal:
    # $dspaceBin import -a -q -s $SAF -c $handle -m $mapfile -e $eperson
    # 
    # resume:
    # $dspaceBin import -a -q -R -s $SAF -c $handle -m $mapfile -e $eperson
    # 
    # Dspace doc:
    # https://wiki.duraspace.org/display/DSDOC4x/Importing+and+Exporting+Items+via+Simple+Archive+Format
    # ===============================
    def intoDspace(self,src_path,collHandle,mapFilePath): # use command to import
        if not self.client:
            raise Exception("Not connected yet!")

        setting = self.setting
        action_flags = setting['action_flags']
        flags = setting['flags']

        cmd = ''
        cmd += setting['dspaceBin'] + ' '
        cmd += setting['command-name'] + ' '
        cmd += action_flags[setting['action']] + ' '
        cmd += flags['unknown'] + ' '
        if setting['toResume']:
            cmd += flags['resume'] + ' '
        cmd += flags['source'] + ' "' + src_path + '" '
        cmd += flags['collection'] + ' ' + collHandle + ' '
        cmd += flags['mapfile'] + ' "' + mapFilePath + '" '
        cmd += flags['eperson'] + ' ' + setting['DspaceIdentity']

        if setting['requireRoot']:
            rootPW = setting['password']
        else:
            rootPW = False
        return __class__.execute(self.client,cmd,rootPW,setting['commandTimeout'])

    def grabMapFile(self,mapFilePath,safCollPath): # get mapfile
        if not self.sftp:
            raise Exception("Not connected yet!")
        sftp = self.sftp

        localMapFilePath = os.path.join(safCollPath,self.setting['localMapFileName'])
        print("download mapfile from [%s] to [%s]..." % (mapFilePath,localMapFilePath))
        sftp.get(mapFilePath,localMapFilePath)
        return localMapFilePath

    def mapFile2mapJson(self,localMapFilePath,localMapJsonDir,name,handle):
        data = {
            'Collection':{
                'name':name,
                'handle':handle,
            },
        }
        items = []
        with open(localMapFilePath) as f:
            for l in f.readlines():
                items.append({
                    'name':l[:l.index('/')-10],
                    'handle':l[l.index('/')-9:].replace('\n','')
                })
        data['items']=items
        mapJsonPath = os.path.join(localMapJsonDir,name + "_" + handle.split('/')[-1] + ".json")
        with open(mapJsonPath, 'w') as outfile:
            json.dump(data, outfile)

        return mapJsonPath

    def cleanup(self,remotepath,mapFilePath,localMapFilePath): # delete mapfile and saf_tmp on server
        if not self.sftp:
            raise Exception("Not connected yet!")
        sftp = self.sftp

        setting = self.setting

        print("Clean up ...")

        if not setting['keepUploadedSAF']:
            print("Remove remote SAF: [%s]..." % remotepath)
            __class__.remove_r(sftp,remotepath)
        if not setting['keepOriMapFile']['remote']:
            print("Remove remote mapfile: [%s]..." % mapFilePath)
            sftp.remove(mapFilePath)
        if not setting['keepOriMapFile']['local']:
            print("Remove local mapfile: [%s]..." % localMapFilePath)
            os.remove(localMapFilePath)

    def importOneSaf(self,safCollPath,collHandle,localMapJsonDir = False):
        SAFColl = os.path.split(os.path.abspath(safCollPath))[1]

        print("Start to Process...")

        remotepath = self.toFS(safCollPath)
        mapFilePath = self.mapFilePath(SAFColl)
        print("into Dspace...")
        cmdResult = self.intoDspace(remotepath,collHandle,mapFilePath)
        
        if cmdResult['retval']:
            raise Exception("Dspace cli reports:\n" + "".join(cmdResult['err']))
        
        localMapFilePath = self.grabMapFile(mapFilePath,safCollPath)
        
        if localMapJsonDir:
            mapJsonPath = self.mapFile2mapJson(localMapFilePath,localMapJsonDir,SAFColl,collHandle)
            print("mapJson is stored here:",mapJsonPath)

        self.cleanup(remotepath,mapFilePath,localMapFilePath)

    def importSAF(self,dirpath,collHandle,localMapJsonDir = False):
        try:
            self.SAFCollList = self.genSAFList(dirpath)
            self.connect()

            for safCollPath in self.SAFCollList:
                self.importOneSaf(safCollPath,collHandle,localMapJsonDir)

        except Exception as e:
            print("Error:\n\t",e)
            return e
        else:
            print("Done without error.")
        
        self.client.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:\n\tpython3 "+sys.argv[0]+" <SAF_path> <handle> [<json_dir>]")
        sys.exit(1)

    main = safSshDspace(loadJsonConfig(os.path.join(os.path.dirname(os.path.realpath(__file__)),'setting.json')))

    if len(sys.argv) == 4:
        localMapJsonDir = sys.argv[3]
    else:
        localMapJsonDir = False

    main.importSAF(sys.argv[1],sys.argv[2],localMapJsonDir)
