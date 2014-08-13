safSshDspace
============

自動將本地端的 SAF 檔案格式使用 SCP 上傳至 DSPACE 伺服器並且 SSH 下指令進行 import

## Requirement

 * Python3
 * [paramiko](https://github.com/paramiko/paramiko) module (provides ssh functionality),use `pip3 install paramiko` to install this module

## Usage

 * create a json file named `setting.json` which have auth information just like below:

    ```
    {
        "hostname":"",
        "username":"",
        "password":"",

        "SAFTmpDir":"",

        "requireRoot":"",
        "dspaceBin":"",
        "mapfileDir":"",
        "DspaceIdentity":""
    }
    ```

 * Use the following command to upload and import SAF:

    ```
    python3 safSshDspace.py <SAF_path> <handle> [<json_dir>]
    ```
