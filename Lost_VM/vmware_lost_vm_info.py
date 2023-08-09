
import ssl, csv, smtplib, paramiko, atexit, pyVim, os, re, dns.resolver
from os.path import basename
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

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


#Function to get info about VM
def VmInfo(vm, VMW_POOL):
    summary = vm.summary
    vmw_pool = VMW_POOL
    vm_name = summary.config.name
    vm_date = vm.config.createDate.strftime("%Y-%m-%d %H:%M")
    #print(vm.config)

    config = vm.config
    devices = config.hardware.device
    vm_disk_summ = 0
    for device in devices:
        if isinstance(device, vim.vm.device.VirtualDisk):
            vm_disk_kb = device.capacityInKB
            vm_disk_gb = vm_disk_kb / 1024 / 1024
            vm_disk_gb_round = (round (vm_disk_gb))
            vm_disk_summ = vm_disk_summ + vm_disk_gb_round
    #make an array with VM details
    vm_param_array = [[vmw_pool, vm_name, vm_date, vm_disk_summ]]
    return vm_param_array
  

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
        

#Function to resolve VM in DNS by its name
def DNSresolve(vm_name):
    vm_name = vm_name
    try:
        socket.gethostbyname(vm_name)
    except socket.gaierror:
        dns_resolv_status = "error"
        dns_resolv_status = str(dns_resolv_status)
    else:
        dns_resolv_status = "ok"
    return dns_resolv_status


def main():
    #Clean up csv file
    csvinfo = "../csv/csvinfovmw.csv" #Save csv file inside 'csv' folder
    clearCSV(cloneinfo)

    #Hard code name of ESXi Pool
    VMW_POOL = 'bft-esxi-pool'

    for VC_HOST in VC_HOSTs: #Loop the array of ESXi hosts
        service_instance = vc_connect(VC_HOST)
        atexit.register(Disconnect, service_instance)
        content = service_instance.RetrieveContent()
 
        for child in content.rootFolder.childEntity:
            if hasattr(child, 'vmFolder'):
                datacenter = child
                #print(child)
                vmFolder = datacenter.vmFolder
                vmList = vmFolder.childEntity #Список с ID всех ВМ
                for vm in vmList:
                    summary = vm.summary
                    vm_name = summary.config.name
                    dns_resolv_state = DNSresolve(vm_name)
                    #Try to resolve VM in DNS
                    if dns_resolv_state == "error":
                    #If VM does not resolve DNS add its details into csv file
                        vm_param_array = VmInfo(vm, VMW_POOL)
                        appendCSV(vm_param_array,cloneinfo)  


if __name__ == '__main__':
    main()
