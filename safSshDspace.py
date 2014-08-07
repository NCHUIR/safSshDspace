import sys,os,re,json
from paramiko import SSHClient,SFTPClient

print("hello world! import success!")


setting = {}

def loadSSHConfig(jsonPath):
    jsonFile=open(jsonPath)
    data = json.load(jsonFile)
    jsonFile.close()
    return data

sshConfig = loadSSHConfig('ssh.json')
print(sshConfig)

print("testing ssh...")
# Testing ssh...
client = SSHClient()
client.load_system_host_keys()
client.connect(
    hostname = sshConfig['host'],
    username = sshConfig['user'],
    password = sshConfig['password'],
)
print("client.exec_command('ls -l') ...\n")
stdin, stdout, stderr = client.exec_command('ls -l')

# client = paramiko.SSHClient()
# client.get_host_keys().add('ssh.example.com', 'ssh-rsa', key)
# client.connect('ssh.example.com', username='strongbad', password='thecheat')
# stdin, stdout, stderr = client.exec_command('ls')
for line in stdout:
    print(line.strip('\n'))

print("exec_command test completed!")

# client needs to start from Transport obj
# sftp = SFTPClient(client)
# print("\nsftp listdir in root:\n",sftp.listdir("/"))

client.close()
