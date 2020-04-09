#!/usr/bin/env python
PROGRAM_NAME = "cg-yml-to-jinja.py"
PROGRAM_DESCRIPTION = """
CloudGenix YML to JINJA Template converter utility
---------------------------------------
This script will convert a CloudGenix YML Site Export file taken from the pull_site script and
convert it into both a JINJA YML Template file and a CSV Parameters file.
"""
import yaml
import csv
import sys
import argparse


sites_version = 'sites v4.5'
elements_version = 'elements v2.3'
csv_out_dict = {}
CLIARGS = {}
yml_input = {}


def open_files():
    print("OPENING FILE")
    print(" USING INPUT FILE:", CLIARGS['Input YML File'])
    yml_dict = {}
    with open(CLIARGS['Input YML File'], 'r') as stream:
        try:
            print(" Opened file successfully")
            yml_dict = yaml.safe_load(stream)
            print(" Loaded YML Successfully")        
        except yaml.YAMLError as exc:
            sys.exit(exc)

    if(sites_version not in yml_dict.keys()):
        sys.exit("ERROR: no sites (" + sites_version + ") found in YML input file")

    if len(yml_dict[sites_version]) > 1:
        print(" WARNING: more than 1 site found. It is recommended that a YML with only 1 site be used")
    return yml_dict

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=PROGRAM_DESCRIPTION
            )
    parser.add_argument('--ignore-nulls', '-I', help='Instruct the script to ignore NULL/Empty values', action="store_true")
    parser.add_argument('--output-yml', '-Y', metavar='outputyml', type=str, default="template-jinja.yml",
                    help='The output file to write the JINJA YML Template. DEFAULT template-jinja.yml')
    parser.add_argument('--output-csv', '-C', metavar='outputcsv', type=str, default="template-parameters.csv",
                    help='The output file to write the CSV Parameters. DEFAULT template-parameters.csv')
    parser.add_argument('Input YML File', metavar='input-yml', type=str, help='The input YML file')

    args = parser.parse_args()
    CLIARGS.update(vars(args)) ##ASSIGN ARGUMENTS to our DICT

def CleanBrackets(item):
    retval = item
    retval = retval.replace("{{ ","")
    retval = retval.replace(" }}","")
    retval = retval.replace("{{","")
    retval = retval.replace("}}","")
    retval = retval.replace(sites_version + ".","")
    retval = retval.replace(sites_version,"")
    retval = retval.replace(" ","_")
    retval = retval.replace(".","_")
    retval = retval.replace("-","_")
    retval = retval.replace("&","_") ##Added support for & character in YML files as JINJA doesnt support this. Thanks Richard Gallagher!
    return retval

### The function of code was modified from Ryder Bush's original YML to JINJA converter
### found at https://github.com/waterswim 
### I have added lines needed to populate the CSV Dict and to permit the ignoring of
### Null parameters
def RecursivelyChangeVals(item, path = ""):
    if ((type(item) == None) or (item is None)) and (CLIARGS['ignore_nulls']):
        return ""
    
    elif (isinstance(item, dict)):
        for key,value in item.items():
            item[key] = RecursivelyChangeVals(value, f"{path}.{key}")
        return item
    elif (isinstance(item, list)):
        for key,value in enumerate(item):
            item[key] = RecursivelyChangeVals(value, f"{path}.{key}")
        return item
    else:
        if (str(item) == "None"):
            csv_out_dict[CleanBrackets(path[1:])] = ""
        else:
            csv_out_dict[CleanBrackets(path[1:])] = str(item)
        path = CleanBrackets(path)
        return f"{{{{{path[1:]}}}}}" 

def go():
    ####RENAME the SITES, and Elements in the YML with Generic Names
    print("Executing Conversion Process")
    
    print(" Renaming SITE Keys")
    site_counter = 0
    for site in list(yml_input[sites_version]):
        site_counter += 1
        new_site_name = "{{site_" + str(site_counter) + "}}"
        yml_input[sites_version][new_site_name] = yml_input[sites_version][site] 
        del yml_input[sites_version][site]
        csv_out_dict[CleanBrackets(new_site_name)] = site
        print(" Renamed site",site_counter,"from",site,"to",CleanBrackets(new_site_name))
        element_counter = 0
        if (type(yml_input[sites_version][new_site_name][elements_version]) == dict): #Ensure that atleast one subelement exists within the site
            for element in list(yml_input[sites_version][new_site_name][elements_version]):   ###Iterate and do the elements within the site
                element_counter += 1
                new_element_name = "{{ " + CleanBrackets(new_site_name) + "_element_" + str(element_counter) + " }}"
                yml_input[sites_version][new_site_name][elements_version][new_element_name] = yml_input[sites_version][new_site_name][elements_version][element]
                del yml_input[sites_version][new_site_name][elements_version][element]
                csv_out_dict[CleanBrackets(new_element_name)] = element

    if(CLIARGS['ignore_nulls']):
        print(" Ignoring NULL and EMPTY Values")
    else:
        print(" Replacing NULL/EMPTY Values")
    #Recursively change all subvalues in the YML DICTIONARY
    print(" Renaming all Key Value pairs to JINJA Template values...")
    RecursivelyChangeVals(yml_input)
    print(" JINJA Value Renaming Complete")

def write_files():
    print("WRITING FILES")
    
    print(" Writing YML JINJA OUTPUT File",CLIARGS['output_yml'] )
    with open(CLIARGS['output_yml'], 'w') as file:  
        documents = yaml.dump(yml_input, file)  ####WRITE the YML Template
        print(" SUCCESS: Wrote YML Template file",CLIARGS['output_yml'])
    
    print(" Writing CSV Parameter OUTPUT File",CLIARGS['output_csv'] )
    with open(CLIARGS['output_csv'], 'w', newline='') as csvoutput: #####WRITE the CSV sample file
        linewriter = csv.writer(csvoutput, delimiter=',', quotechar='"')
        linewriter.writerow(csv_out_dict.keys())
        linewriter.writerow(csv_out_dict.values())
        print(" SUCCESS: Wrote CSV Parameter file",CLIARGS['output_csv'])

if __name__ == "__main__":
    parse_arguments()
    yml_input = open_files()
    go()
    write_files()
