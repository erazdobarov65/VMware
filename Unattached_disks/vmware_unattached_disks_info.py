
import ssl, csv, smtplib, atexit, pyVim, os, base64, urllib.request, urllib.parse, socket
from os.path import basename
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
from pyVim.task import WaitForTask

# Enter you connection details
VC_HOSTs = ["esxi_host1_name.xxx.xx", "esxi_host2_name.xxx.xx"] #array of hypervisor ESXi hosts
VC_USER        = "ESXi_user" #Read-only user
VC_PASS        = "ESI_password"

#Function to establish connection with ESXi host
def vc_connect(VC_HOST):
    context = ssl._create_unverified_context()
    si = None
    si = SmartConnect(host=VC_HOST, port=443, user=VC_USER, pwd=VC_PASS, sslContext=context)
    return si

#Function to disconnect from ESXi host
def vc_disconnect(service_instance):
    Disconnect(service_instance)

#Get info about disks tha are attahched to VMs
def find_vm_disk(vm, VC_HOST, VIRT_NAME, VMW_POOL):
    # VM_name
    summary = vm.summary
    virt_name = VIRT_NAME
    vmw_pool = VMW_POOL
    vm_name = summary.config.name
    vm_date = vm.config.createDate.strftime("%Y-%m-%d %H:%M")
    #print(vm.config)
 
    vm_disk_array = []
    config = vm.config
    devices = config.hardware.device
    vm_disk_summ = 0
    for device in devices:
        #print(device)
        if isinstance(device, vim.vm.device.VirtualDisk):
            vm_disk_array.append(vm_disk)
    return vm_disk_array


#Function to clean up csv
def clearCSV(vmhostinforesources):
    filename = vmhostinforesources
    f = open(filename, "w+")
    f.close()


#Function to add entry into csv file
def appendCSV(title, vmhostinforesources):
    with open(vmhostinforesources, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerows(title)


#Function to search for disks that are not attched to VMs
def find_all_disk(datacenters, VMW_POOL, diskinfo, vm_disks_array_host_all):
    #Here we use DatastoreBrowser classes to find disks inside datastores
    queryDetailsDisk = vim.host.DatastoreBrowser.VmDiskQuery.Details()
    queryDetailsDisk.capacityKb = True
    queryDetailsDisk.diskType = True
    queryDetailsDisk.hardwareVersion = True
    queryDetailsDisk.thin = True
    search_spec = vim.host.DatastoreBrowser.SearchSpec(query=[vim.host.DatastoreBrowser.VmDiskQuery(details=queryDetailsDisk)])
    
    for dc in datacenters:
        for ds in dc.datastore:
            #print(ds.summary)
            task = ds.browser.SearchSubFolders("[%s]" % ds.name, search_spec)
            while task.info.state != "success":
                pass
            for sub_folder in task.info.result:
                #print(sub_folder)
                ds_store = sub_folder.folderPath
                #print(ds_store)
                ds_store_list = ds_store.split()
                ds_store_list_name = str(ds_store_list[0])
                ds_store_list_name_str = ds_store_list_name[1:-1]
                for file in sub_folder.file:
                    ds_file = file.path
                    ds_file_str = ds_file[:-5]
                    ds_file_size_kb = file.capacityKb /1024 /1024
                    ds_file_size_gb = round(ds_file_size_kb)
                    ds_file_disk_path = ds_store +'/'+ ds_file
                    if ds_file_disk_path not in vm_disks_array_host_all:
                        disk_param_array = [[VMW_POOL, ds_store_list_name_str, ds_file_str, ds_file_size_gb]]
                        appendCSV(disk_param_array, diskinfo)
    return disk_param_array  

#Function to search for ISO disks
def find_iso_disk(datacenters, VMW_POOL, diskinfo):
    queryFileDetails = vim.host.DatastoreBrowser.FileInfo.Details()
    #queryDetailsDisk.capacityKb = True
    #ueryDetailsDisk.diskType = True
    queryFileDetails.fileSize = True
    queryFileDetails.fileType = True
    #queryDetailsDisk.hardwareVersion = True
    #queryDetailsDisk.thin = True
    #search_spec = vim.HostDatastoreBrowserSearchSpec(query=[vim.host.DatastoreBrowser.FileInfo(details=queryDetailsDisk)])
    search_spec = vim.host.DatastoreBrowser.SearchSpec()
    search_spec.details = queryFileDetails
    
    #all_disks_array = []
    for dc in datacenters:
        for ds in dc.datastore:
            #print(ds.summary)
            task = ds.browser.SearchSubFolders("[%s]" % ds.name, search_spec)
            while task.info.state != "success":
                pass
            for sub_folder in task.info.result:
                #print(sub_folder)
                ds_store = sub_folder.folderPath
                #print(ds_store)
                ds_store = str(ds_store)
                if ds_store == "[DATASTORE_NAME] ISOs": #make sure to enter here your custom 'DATASTORE_NAME'. That is where you keep all ISO images
                    ds_store_list = ds_store.split()
                    ds_store_list_name = str(ds_store_list[0])
                    ds_store_list_name_str = ds_store_list_name[1:-1]
                    for file in sub_folder.file:
                        ds_file = file.path
                        ds_file_str = ds_file
                        ds_file_size_kb = file.fileSize /1024 /1024
                        ds_file_size_gb = round(ds_file_size_kb)
                        disk_param_array = [[VMW_POOL, ds_store_list_name_str, ds_file_str, ds_file_size_gb]]
                        appendCSV(disk_param_array, diskinfo)
                    exit()
                else:
                    pass
    return disk_param_array 
    
def main():
    #Clean up csv file
    diskinfo = "../csv/diskinfo_vmw.csv" #save your csv file with disk info inside 'csv' folder
    diskiso = "../csv/diskiso_vmw.csv" #save your csv file with ISO info inside 'csv' folder
    #Clean up csv files
    clearCSV(diskinfo)
    clearCSV(diskiso)
    
    #Hard code VMware pool
    VMW_POOL = 'bft-esxi-pool'

    vm_disks_array_total_host_all =  []
    for VC_HOST in VC_ALLHOSTs: #Loop through all ESXi hosts in the array
        service_instance = vc_connect(VC_HOST)
        content = service_instance.RetrieveContent()

        vm_disks_array_total_host= []
        for child in content.rootFolder.childEntity:
            if hasattr(child, 'vmFolder'):
                datacenter = child
                vmFolder = datacenter.vmFolder
                vmList = vmFolder.childEntity #Список с ID всех ВМ
                for vm in vmList:
                    summary = vm.summary
                    vm_name = summary.config.name
                    VC_HOSTStr = str(VC_HOST)
                    VC_HOSTStr = VC_HOSTStr[:-7]                     
                    vm_disks_array = find_vm_disk(vm, VC_HOSTStr, VMW_NAME, VMW_POOL)
                    vm_disks_array_total_host += vm_disks_array # Create common array from all VMs inside hypervizor
                    #print(vm_disks_array)
        #print(vm_disks_array_total)
        vm_disks_array_total_host_all += vm_disks_array_total_host #Create coomon array from all hypervizors
    vc_disconnect(service_instance)

    for VC_HOST in VC_ALLHOSTs: #Loop through all ESXI hosts in the array
        try:
            service_instance = vc_connect(VC_HOST)
            content = service_instance.RetrieveContent()
            datacenters = content.rootFolder.childEntity
            #datastores = datacenter.datastore
            find_all_disk(datacenters, VMW_POOL, diskinfo, vm_disks_array_total_host_all)
            find_iso_disk(datacenters, VMW_POOL, diskiso)
            if socket.gethostbyname(VC_HOST): # In case we succeed to connect to the first ESXi host in the array, we exit the loop, since all hosts have inside one cluster hve the same set of datasores
                exit()
            #print(all_disks_array)
        except socket.gaierror:
            print(f"Can not connect to {VC_HOST}")
        else:
            continue # If we fail to connect to the first ESXi host in the array we move to the next one

    vc_disconnect(service_instance)
    


if __name__ == '__main__':
    main()
