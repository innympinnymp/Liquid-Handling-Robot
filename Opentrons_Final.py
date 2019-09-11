from opentrons import labware,instruments
import csv
#import system for input
import sys

#the csv is changed to list so that it can be accessed through latter portion of the code for transferring
def csv_to_list(vol_multiplier): 
    new_fields = ['ingredient_num','vols','run_num','discard_tips']
    all_list = []
    with open('/data/MixingExp3.csv', newline='') as example:
        reader = csv.DictReader(example)#read the CSV file and match the column name with column
        fields = reader.fieldnames#read first row is column name
        fields_len = len(fields)#number of column in CSV
        instruction_list = [[] for x in range(fields_len - 2)] #exclude first and last column in csv from R
        run_num = ''
        #for loop for looping around the list created which some components of transffering such as number of ingredients, total volume of solution, number of runs, tips discards

        for row in reader:
            run_num = row["Run"]            
            for i in range(1,fields_len-1): # loop in csv column only solution for experiment, exclude Run and Dimen column
                instruction_list[i-1].append({'ingredient_num':i,'vols':int(float(row[fields[i]]) * vol_multiplier),'run_num':run_num,'discard_tips':'no'})
                #group by ingredient number
        
        #discard tips when ingredient is changed 
        last_run = int(run_num)
        for inst in instruction_list:            
            inst[last_run - 1]['discard_tips'] = 'yes'
            all_list = all_list + inst
        
#After each ingredient is finished transferring, there is a key waiting for users to see the warnings or adding new ingredients
def waitForKey():
    input('Press enter to continue...')

#prompt the users the number of slots for source ingredient
max_src_slot = int(input("Please input number of Plate Slot for ingredient: ")) 
#define the configuration of the experiment by telling the users where destination plates,source plates,tipracks are
max_dest_slot = 11 - max_src_slot - 1 
min_dest_slot = max_src_slot + 2 
tip_slot = max_src_slot +1 #place the tip slot next to the src_plate
plate_containers = [ None for x in range(11)] #create 11 arrays
print("Load tiprack-1000ul at slot no. ",(tip_slot))
#load 1000ul tips
tiprack1000ul = labware.load('tiprack-1000ul',str(tip_slot))
P1000 = instruments.P1000_Single( mount= 'right', tip_racks=[tiprack1000ul])

#######
## create and load customized 20ml scintillation vials plate
#for loop is written as if the plate cannot be found in the default labware list, the new labware will be created
plate_name='glass_20ml_v2_In'
if plate_name not in labware.list():
    ## create if not found
    labware.create(
        plate_name,                    
        grid=(3, 2),       #specify dimensions of the dimensions of the plates(columns,rows) 
        spacing=(33,33),   #distances (mm) between each (column, row)
        diameter=16,       #diameter (mm) of each well on the plate
        depth=50,          #height of each well (mm)
        volume = 20000     #maximum volume that can be put for each well (um)
    )   

for slot in range(max_src_slot):
    plate_containers[slot] = labware.load(plate_name, str(slot+1))
print("Load experiment destination plate tuberack: ",plate_name, " for ",10-max_src_slot," slot")
dest_slot_start = max_src_slot + 1

#print out the slot no. so users know where to put plates in which slot
for slot in range(dest_slot_start,11):
    print("Load ",plate_name," at slot no. ",(slot +1))
    plate_containers[slot] = labware.load(plate_name, str(slot+1))
#prompt the user for the final solution
vol_multiplier = int(input("Please input final solution volume as number in ml:"))*1000
print("Volume multiplier: ",vol_multiplier)
transfer_list = csv_to_list(vol_multiplier)

##################################################################################

#initializing all the transferring components and wells numbers
max_vol_per_well = 20000 # 20ml = 20000 ul
max_wells_per_slot = 6
max_src_vol = max_vol_per_well *max_wells_per_slot* max_src_slot
# max_src_slot from input, max_dest_slot from calculate, min_dest_slot is max_src + 2
last_ingredient = 0
sum_tx_vol = 0
sum_ing_vol_all = 0
src_plate_num = 0
src_well_num = 0

dest_plate_num = 0
dest_well_num = 0

for tx in transfer_list:
    current_ingredient = tx['ingredient_num']
    ## determine ingrendient changed and pick up new tips
    if(last_ingredient != current_ingredient):
        P1000.pick_up_tip()
        print("PREPARE INGREDIENT",current_ingredient)
        print("Please Fill the whole slot 1 to ",max_src_slot," with ingredient ",current_ingredient)
        waitForKey()        
        last_ingredient = current_ingredient
        ## reset source reference
        src_plate_num = 0
        src_well_num = 0
        sum_tx_vol = 0 
        sum_ing_vol_all = 0

    ######
    ##determine how manys destination plates needed according to the number of runs
    sample_num = int(tx['run_num'])-1
    dest_plate_num = int(sample_num / max_wells_per_slot) + min_dest_slot - 1 # minus 1 for array index start at zero
    dest_well_num = (sample_num % max_wells_per_slot) # no need minus 1 becuase % is included index start at zero itself
    #make sure that the destination plates not exceed the maximum number of slot
    if(dest_plate_num >= 11):
        print('ERROR!!!! number of destination plate is greater than maximum slot')
        exit(1)
    ######
    ## determine source plate and well from transfer volume
    tx_vol = tx['vols']
    #if the well of the source volume is below 20% volume, there wil be a warning sign
    if(max_src_vol * 0.8 < sum_ing_vol_all ):
        print('WARNING. Current ingredient in all slot is transfered more than 80%.')
        print('Please refill the all source slot vials with ingredient',current_ingredient)
        waitForKey()
        ## reset all src reference
        src_plate_num = 0
        src_well_num = 0
        sum_tx_vol = 0
        sum_ing_vol_all = 0
    #When the volume of the well is not enough, the transfer will move to next well
    if((tx_vol + sum_tx_vol) > max_vol_per_well): 
        if(src_well_num != (max_wells_per_slot -1 )): 
            ## have more well, move to next well, same slot
            src_well_num = src_well_num +1
        else: ## last well of slot, move to next plate
            if(src_plate_num != (max_src_slot - 1)): 
                ## have more slot, move to next slot, first well
                src_plate_num = src_plate_num + 1
                src_well_num = 0
            else:## when at the last plate with not enough source ingredients, warning sign pops up
                print('Please refill the all source slot vials with ingredient',current_ingredient)
                waitForKey()
                src_plate_num = 0
                src_well_num = 0
                sum_ing_vol_all = 0
                sum_tx_vol = 0 ## reset sum transfer volume on well        

    #perform the transfer process from specified source plates/wells to destination pates/wells
    P1000.transfer(tx_vol,
    plate_containers[src_plate_num].wells(src_well_num),
    plate_containers[dest_plate_num].wells(dest_well_num),
    new_tip='never'
    )
    #print out the instructions to communicate with the users
    print('Transfer ingredient',current_ingredient
    ,'from plate',(src_plate_num +1), plate_containers[src_plate_num].wells(src_well_num)
    ,'to plate',(dest_plate_num+1), plate_containers[dest_plate_num].wells(dest_well_num)
    ,'volume = ',(tx_vol/1000),'ml' )    
    sum_tx_vol = sum_tx_vol+ tx_vol
    sum_ing_vol_all = sum_ing_vol_all+ tx_vol
   
    #discard the tips when ingredients are changed
    if(tx['discard_tips'] == 'yes'):
        P1000.drop_tip()


    



