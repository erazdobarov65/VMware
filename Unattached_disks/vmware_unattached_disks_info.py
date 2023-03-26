
import ssl, csv, smtplib, atexit, pyVim, os, base64, urllib.request, urllib.parse, socket
from os.path import basename
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
#from tools import pchelper, service_instance
from pyVim.task import WaitForTask

#
VC_ALLHOSTs = ["hyp07.ftc.ru", "hyp08.ftc.ru", "hyp09.ftc.ru", "hyp10.ftc.ru", "hyp16.ftc.ru"]
VC_USER        = "ops" #Rundeck user
VC_PASS        = "2019@VMops!User"

## Функция соединения с ESXi
def vc_connect(VC_HOST):
    context = ssl._create_unverified_context()
    si = None
    si = SmartConnect(host=VC_HOST, port=443, user=VC_USER, pwd=VC_PASS, sslContext=context)
    return si

## Функция отключения от ESXi
def vc_disconnect(service_instance):
    Disconnect(service_instance)



# Получаем инфо по дискам, которые привязаны к ВМ
def find_vm_disk(vm, VC_HOST, VIRT_NAME, VMW_POOL):
    # VM_name
    summary = vm.summary
    virt_name = VIRT_NAME
    vmw_pool = VMW_POOL
    #ext_data = vm.extensiondata
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
            vm_disk = device.backing.fileName
            if  vm_disk == "[BFT-G350-VMW01] ISOs/cobbler-boot.iso":
               print(device)
            vm_disk_array.append(vm_disk)
    return vm_disk_array

    #vm_param_array = [[virt_name, vmw_pool, vm_name, vm_date, vm_disk_summ]]
    #return vm_param_array




#Очищаем csv
def clearCSV(vmhostinforesources):
    filename = vmhostinforesources
    f = open(filename, "w+")
    f.close()


#Добавляем записи в csv
def appendCSV(title, vmhostinforesources):
    with open(vmhostinforesources, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerows(title)



## Функция поиска дисков, которые не привязаны к ВМ
def find_all_disk(datacenters, VMW_POOL, diskinfo, vm_disks_array_host_all):
    queryDetailsDisk = vim.host.DatastoreBrowser.VmDiskQuery.Details()
    queryDetailsDisk.capacityKb = True
    queryDetailsDisk.diskType = True
    #queryDetailsDisk.fileType = True
    #queryDetailsDisk.fileSize = True
    queryDetailsDisk.hardwareVersion = True
    queryDetailsDisk.thin = True
    search_spec = vim.host.DatastoreBrowser.SearchSpec(query=[vim.host.DatastoreBrowser.VmDiskQuery(details=queryDetailsDisk)])
    
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
                ds_store_list = ds_store.split()
                ds_store_list_name = str(ds_store_list[0])
                ds_store_list_name_str = ds_store_list_name[1:-1]
                for file in sub_folder.file:
                    ds_file = file.path
                    #if ds_file == "0004fb00001200007c38bcdaa87a89af.vmdk":
                    #    print(sub_folder)
                    ds_file_str = ds_file[:-5]
                    ds_file_size_kb = file.capacityKb /1024 /1024
                    ds_file_size_gb = round(ds_file_size_kb)
                    ds_file_disk_path = ds_store +'/'+ ds_file
                    #print(ds_file_disk_path)
                    #if ds_file_disk_path == "[BFT-G350-VMW01]/cobbler-boot-new.iso":
                    #    print(ds_file_disk_path)     
                    if ds_file_disk_path not in vm_disks_array_host_all:
                    #all_disks_array.append(ds_file_disk_path)
                    #print(ds_file_size_gb)
                        disk_param_array = [[VMW_POOL, ds_store_list_name_str, ds_file_str, ds_file_size_gb]]
                        appendCSV(disk_param_array, diskinfo)
    return disk_param_array  

## Функция поиска ISO дисков
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
                if ds_store == "[BFT-G350-VMW01] ISOs":
                    ds_store_list = ds_store.split()
                    ds_store_list_name = str(ds_store_list[0])
                    ds_store_list_name_str = ds_store_list_name[1:-1]
                    for file in sub_folder.file:
                        ds_file = file.path
                        #if ds_file == "0004fb00001200007c38bcdaa87a89af.vmdk":
                        #    print(sub_folder)
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
    #Очищаем CSV
    diskinfo = "/u/ckdba/unix_service/Infotask/check_unattached_vm_disk/csv/diskinfo_vmw.csv"
    diskiso = "/u/ckdba/unix_service/Infotask/check_unattached_vm_disk/csv/diskiso_vmw.csv"
    clearCSV(diskinfo)
    clearCSV(diskiso)

    VMW_NAME = 'esx'
    VMW_POOL = 'bft-esxi-pool'

    vm_disks_array_total_host_all =  []
    for VC_HOST in VC_ALLHOSTs: #Перебираем все ESXi из массива
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
                    vm_disks_array_total_host += vm_disks_array # Формируем общий массив со всех ВМ
                    #print(vm_disks_array)
        #print(vm_disks_array_total)
        vm_disks_array_total_host_all += vm_disks_array_total_host #Форируем общий массив со всех хостов
    vc_disconnect(service_instance)

    for VC_HOST in VC_ALLHOSTs: #Перебираем все ESXi из массива
        try:
            VC_HOSTStr = str(VC_HOST)
            VC_HOSTStr = VC_HOSTStr[:-7]  
            service_instance = vc_connect(VC_HOST)
            #atexit.register(Disconnect, service_instance)
            content = service_instance.RetrieveContent()
            datacenters = content.rootFolder.childEntity
            #datastores = datacenter.datastore
            find_all_disk(datacenters, VMW_POOL, diskinfo, vm_disks_array_total_host_all)
            find_iso_disk(datacenters, VMW_POOL, diskiso)
            if socket.gethostbyname(VC_HOST): # если удалось подключится к первому хосту, то не идем дальше по циклу, т.к. к каждому хосту подключен одинаковый набор датасторов
                exit()
            #print(all_disks_array)
        except socket.gaierror:
            print(f"Can not connect to {VC_HOST}")
        else:
            continue # Если не удалось подключиться к первому хосту идем дальше по циклу

    vc_disconnect(service_instance)
    


if __name__ == '__main__':
    main()
