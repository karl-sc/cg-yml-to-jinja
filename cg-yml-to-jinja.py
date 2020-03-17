#!/usr/bin/env python
PROGRAM_NAME = "cg-site-health-check.py"
PROGRAM_DESCRIPTION = """
CloudGenix script
---------------------------------------

TODO: Jitter/Latency/Loss measurements per link
TODO: Determine endpoint for service links (which zscaler node/prisma cloud)
TODO: Only Major and Critical alarms/alerts

"""
from cloudgenix import API, jd
import os
import sys
import argparse
from fuzzywuzzy import fuzz
from datetime import datetime,timedelta   
import numpy as np
import requests 
import json
from lxml import html
import cloudgenix_idname

###SYSTEM DEFAULTS
print_console = True
print_borders = True
print_colors = True

print_html = False ###INCOMPLETE

T1 = "T1"
P1 = "P1"
H1 = "H1"
H2 = "H2"
B0 = "B0"
B1 = "B1"

style = "style"
data = "data"
theader = "header"
boldfirst = "boldfirst"
html_buffer = '<!DOCTYPE html><html><meta charset="utf-8"><title>CloudGenix Site Health Check</title><br>'
last_style = ""

dns_trt_thresholds = {
    'fail': 120,
    'warn': 50
}

CLIARGS = {}
cgx_session = API(update_check=False)              #Instantiate a new CG API Session for AUTH
diff_hours = 24              #Hours to look back at

pan_service_dict = {
                "Prisma Access": 'q8kbg3n63tmp',
                "Prisma Cloud Management": "61lhr4ly5h9b",
                "Prisma Cloud": '1nvndw0xz3nd',
                "Prisma SaaS": 'f0q7vkhppsgw',
}

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def convert_style_html(text):
    text = text.replace(bcolors.HEADER, '</div><div style="font-weight: bold; display: inline-block; ">')
    text = text.replace(bcolors.OKBLUE, '</div><div style="text-decoration-color: blue; display: inline-block;">')
    text = text.replace(bcolors.OKGREEN, '</div><div style="text-decoration-color: GREEN; display: inline-block;">')
    text = text.replace(bcolors.WARNING, '</div><div style="text-decoration-color: yellow; display: inline-block;;">')
    text = text.replace(bcolors.FAIL, '</div><div style="text-decoration-color: RED; display: inline-block;">')

    text = text.replace(bcolors.BOLD, '</div><div style="font-weight: bold; display: inline-block;">')
    text = text.replace(bcolors.UNDERLINE, '</div><div style="text-decoration: underline; display: inline-block;">')

    text = text.replace(bcolors.ENDC, '</div>')

    if not(str(text).startswith("<div>")):
        text = '<div style="display: inline-block;">' + text
    if not(str(text).endswith("</div>")):
        text = text + "</div>"
    return(text)

def pBold(str_to_print):
    if(print_colors):
        return(bcolors.BOLD + str_to_print + bcolors.ENDC)
    return(str_to_print)

def pFail(str_to_print):
    if(print_colors):
        return(bcolors.FAIL + str_to_print + bcolors.ENDC)
    return(str_to_print)

def pPass(str_to_print):
    if(print_colors):
        return(bcolors.OKGREEN + str_to_print + bcolors.ENDC)
    return(str_to_print)

def pWarn(str_to_print):
    if(print_colors):
        return(bcolors.WARNING + str_to_print + bcolors.ENDC)
    return(str_to_print)

def pExceptional(str_to_print):
    if(print_colors):
        return(bcolors.OKBLUE + str_to_print + bcolors.ENDC)
    return(str_to_print)

def pUnderline(str_to_print):
    if(print_colors):
        return(bcolors.UNDERLINE + str_to_print + bcolors.ENDC)
    return(str_to_print)

def dns_trt_classifier(dns_trt_time):
    if( dns_trt_time > dns_trt_thresholds['fail']):
        return pFail(str(dns_trt_time))
    elif (dns_trt_time > dns_trt_thresholds['warn']):
        return pWarn(str(dns_trt_time))
    else:
        return pPass(str(dns_trt_time))

def metric_classifier(value, expected, error_percentage_as_decimal, warn_percentage_as_decimal=0.05):
    if (value < (expected - ( expected * error_percentage_as_decimal ) )):
        return pFail(str(value))
    
    if (value >= expected + (expected * error_percentage_as_decimal * 2) ):
        return pExceptional(str(value))

    if (value >= expected - (expected * warn_percentage_as_decimal) ):
        return pPass(str(value))
    
    return pWarn(str(value))
    
class border_char_class:
    dl = u'\u255a'
    ul = u'\u2554'
    dc = u'\u2569'
    uc = u'\u2566'
    ur = u'\u2557'
    lc = u'\u2560'
    u = u'\u2550'
    c = u'\u256c'
    l = u'\u2551'
    rc = u'\u2563'
    dr = u'\u255d'

class low_res_border_char_class:
    dl = '*'
    ul = '+'
    dc = '+'
    uc = '+'
    ur = '+'
    lc = '+'
    u = '-'
    c = '+'
    l = '|'
    rc = '+'
    dr = '+'

def true_len(input_str):
    text = str(input_str)
    if (type(input_str) == str):
        text = text.replace(bcolors.HEADER, '')
        text = text.replace(bcolors.OKBLUE, '')
        text = text.replace(bcolors.OKGREEN, '')
        text = text.replace(bcolors.WARNING, '')
        text = text.replace(bcolors.FAIL, '')
        text = text.replace(bcolors.BOLD, '')
        text = text.replace(bcolors.UNDERLINE, '')
        text = text.replace(bcolors.ENDC, '')
        return len(text)
    return len(input_str)

def uprint(input_array):
    first_item = True
    last_item = False
    global last_style
    item_counter = 0
    if print_console:    
        global print_borders
        if (print_borders):
            dbbox = border_char_class
        else:
            dbbox = low_res_border_char_class

        for item in input_array:
            item_counter += 1
            if (item_counter == len(input_array)):
                last_item = True
            if (item['style'] == "P1"):
                if (last_style != ""):
                    print(" ")
                text = item['data']
                item_len = true_len(text)
                print( dbbox.ul + (dbbox.u*item_len) + dbbox.ur)
                print( dbbox.l + pBold(text)+ dbbox.l)
                print( dbbox.lc + (dbbox.u*item_len)+ dbbox.dr)
            elif (item['style'] == "H1"):
                if (last_style != "P1"):
                    print(dbbox.l)
                text = item['data'] 
                item_len = true_len(text)
                print(dbbox.l + dbbox.ul + (dbbox.u*item_len) + dbbox.ur)
                print(dbbox.l + dbbox.l + pBold(text)+ dbbox.l)
                print(dbbox.l + dbbox.lc + (dbbox.u*item_len)+ dbbox.dr)
            elif (item['style'] == "H2"):
                text = item['data'] 
                item_len = true_len(text)
                print(dbbox.l + dbbox.ul + (dbbox.u*item_len) + dbbox.ur)
                print(dbbox.l + dbbox.l + pBold(text) + dbbox.l )
                print(dbbox.l + dbbox.lc + (dbbox.u*item_len)+ dbbox.dr)
            elif (item['style'] == "B1"):
                text = item['data'] 
                print(dbbox.l + dbbox.l + (text))
            elif (item['style'] == "B0"):
                text = item['data'] 
                print(dbbox.l + (text))
                
            elif (item['style'] == "T1"):
                if ("header" not in item.keys()):
                    item['header'] = " "
                if ("boldfirst" not in item.keys()):
                    item['boldfirst'] = True
                table_data = np.array(item['data'])
                if (true_len(table_data.shape) != 2):
                    print ("ERROR, non 2d square data passed to table print function")
                    return False
                table_column_lengths = []
                for iterate in range(table_data.shape[1]):
                    table_column_lengths.append(0)
                for row in table_data:
                    c_count = 0
                    for column in row:
                        mytype = type(column)
                        if ("str" in str(type(column)) ):
                            if (true_len(str(column)) > table_column_lengths[c_count]):
                                table_column_lengths[c_count] = true_len(str(column))
                        else:
                            if (true_len(str(column)) > table_column_lengths[c_count]):
                                table_column_lengths[c_count] = true_len(str(column))
                        c_count += 1
                if (sum(table_column_lengths) < true_len(item['header'])):
                    extra_column_divider_counts = (true_len(table_column_lengths) - 2)
                    len_sum_of_data = sum(table_column_lengths)
                    header_len = true_len(item['header'])
                    addition = (header_len - len_sum_of_data) - extra_column_divider_counts
                    table_column_lengths[0] += addition - 1
                    
                    header_len = true_len(item['header'])
                    table_width = header_len ##width without edge borders
                else:
                    extra_column_divider_counts = (true_len(table_column_lengths)) - 1
                    len_sum_of_data = sum(table_column_lengths)
                    header_len = len_sum_of_data + extra_column_divider_counts
                    table_width = header_len ##width without edge borders
                if ((item['header'] != " ")):
                    print(dbbox.l + dbbox.ul + (dbbox.u*table_width) + dbbox.ur )
                    added_padding = len(str(item['header'])) - true_len(str(item['header']))
                    justified_header = str(item['header']).ljust(table_width + added_padding)
                    print(dbbox.l + dbbox.l + pBold(justified_header)  + dbbox.l)
                    
                    ###print header trailer
                    print(dbbox.l + dbbox.lc, end = "")
                    for iterate in range(table_data.shape[1]):
                        print((dbbox.u * table_column_lengths[iterate]), end = '')
                        c_count += 1
                        if (iterate == table_data.shape[1] - 1):
                            print(dbbox.rc)
                        else:
                            print(dbbox.uc, end="")
                else:
                    print(dbbox.l + dbbox.ul + (dbbox.u*table_width) + dbbox.ur )
                #print data
                r_count = 0
                for row in table_data:
                    print(dbbox.l + dbbox.l, end = "")
                    c_count = 0
                    is_first = True
                    for column in row:
                        added_padding = len(str(column)) - true_len(str(column))
                        if is_first:
                            print( pBold(
                                str(column).ljust(table_column_lengths[c_count] + added_padding)), end = '')
                            
                            is_first = False
                        else:
                            print(  
                                str(column).rjust(table_column_lengths[c_count] + added_padding), end = '')
                        c_count += 1
                        if (true_len(row) == c_count): #is this last?
                            if (r_count == table_data.shape[1]):
                                print(dbbox.rc)
                            else:
                                print(dbbox.l)
                        else:
                            print(dbbox.l, end="")
                #print trailer
                print(dbbox.l + dbbox.dl, end = "")
                for iterate in range(table_data.shape[1]):
                    print((dbbox.u * table_column_lengths[iterate]),end = '')
                    if (iterate == table_data.shape[1] - 1):
                        print(dbbox.dr)
                    else:
                        print(dbbox.dc, end='')
                    c_count += 1
                    ###########END of TABLE PRINTER #######
            last_style = item['style']
            if (last_item):
                print(dbbox.dl + (dbbox.u*item_len))
    if (print_html):
        global html_buffer
        for item in input_array:
            if (item['style'] == "P1"):
                text = item['data'] 
                html_buffer += '<br><h1>' + text + '</h1>'
            elif (item['style'] == "H1"):
                text = item['data'] 
                html_buffer += '<h1>' + text + '</h1>'
            elif (item['style'] == "H2"):
                text = item['data'] 
                html_buffer += '<h2>' + text + '</h2>'
            elif (item['style'] == "B1"):
                text = item['data'] 
                html_buffer += '<body>' + text + '</body>'
            elif (item['style'] == "B0"):
                text = item['data'] 
                html_buffer += '<h3>' + text + '</h3>'
            elif (item['style'] == "T1"):
                if(type(item['data']) == list): ###TBLEHEADER HERE
                    for rows in item[data]:
                        if(type(item['data']) == list):
                            for cell in rows:
                                text = cell
                                html_buffer += "asdad"
                else:
                    html_buffer += '<body>' + str(item['data']) + '</body>'
                print(text)

def getpanstatus(webcontent, str_service):
    services_list = webcontent.xpath('//*[@data-component-id="' + str_service + '"]/span')
    if (len(services_list) == 4):
        service_status = (services_list[2].text).lstrip().rstrip()
    else:
        service_status = (services_list[1].text).lstrip().rstrip()
    return service_status

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=PROGRAM_DESCRIPTION
            )
    parser.add_argument('--token', '-t', metavar='"MYTOKEN"', type=str, 
                    help='specify an authtoken to use for CloudGenix authentication')
    parser.add_argument('--authtokenfile', '-f', metavar='"MYTOKENFILE.TXT"', type=str, 
                    help='a file containing the authtoken')
    parser.add_argument('--site-name', '-s', metavar='SiteName', type=str, 
                    help='The site to run the site health check for', required=True)
    parser.add_argument('--no-colors', '-c',   action="store_true",
                    help='disable colors and fonts')
    parser.add_argument('--no-borders', '-b',   action="store_true",
                    help='disable ascii borders')
    args = parser.parse_args()
    CLIARGS.update(vars(args)) ##ASSIGN ARGUMENTS to our DICT
    if (CLIARGS['no_colors']):
        global print_colors
        print_colors = False
    if (CLIARGS['no_borders']):
        global print_borders
        print_borders = False

def authenticate():
    print_array = []
    print_array.append({ style: P1, data: "Authentication"})
    user_email = None
    user_password = None
    
    print_array.append({ style: H1, data: "Checking Authentication Method"})
    ##First attempt to use an AuthTOKEN if defined
    if CLIARGS['token']:                    #Check if AuthToken is in the CLI ARG
        CLOUDGENIX_AUTH_TOKEN = CLIARGS['token']
        print_array.append({ style: B1, data: "Using " + pBold("AUTH TOKEN") + " from CLI argument parameter"})
    elif CLIARGS['authtokenfile']:          #Next: Check if an AuthToken file is used
        tokenfile = open(CLIARGS['authtokenfile'])
        CLOUDGENIX_AUTH_TOKEN = tokenfile.read().strip()
        print_array.append({ style: B1, data: "Using " + pBold("AUTH TOKEN FILE") + " from " + pUnderline(CLIARGS['authtokenfile']) })
    elif "X_AUTH_TOKEN" in os.environ:              #Next: Check if an AuthToken is defined in the OS as X_AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
        print_array.append({ style: B1, data: "Using " + pBold("X_AUTH_TOKEN") + " from environment variable in shell"})
    elif "AUTH_TOKEN" in os.environ:                #Next: Check if an AuthToken is defined in the OS as AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
        print_array.append({ style: B1, data: "Using " + pBold("AUTH_TOKEN") + " from environment variable in shell"})
    else:                                           #Next: If we are not using an AUTH TOKEN, set it to NULL        
        CLOUDGENIX_AUTH_TOKEN = None
        print_array.append({ style: B1, data: "Attempting Interactive Login..."})
    ##ATTEMPT AUTHENTICATION
    if CLOUDGENIX_AUTH_TOKEN:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print_array.append({ style: T1, data: [ [ pFail("ERROR") , "AUTH_TOKEN login failure, please check token." ]]})
            uprint(print_array)
            sys.exit()
    else:
        uprint(print_array)
        while cgx_session.tenant_id is None:
            cgx_session.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not cgx_session.tenant_id:
                user_email = None
                user_password = None            
    print_array.clear()
    print_array.append({ style: P1, data: "Authentication Result"})
    print_array.append({ style: T1, data: [ [ pPass("SUCCESS") , "Authentication Completed Successfully" ]]})
    uprint(print_array)

def go():
    idname =  cloudgenix_idname.CloudGenixIDName(cgx_session)
    vpnpaths_id_to_name = idname.generate_anynets_map()
    print_array = []

    #########   START: TENANT INFORMATION  #########
    print_array.clear()
    print_array.append({ style: P1, data: "TENANT Information"})
    resp = cgx_session.get.tenants()
    if resp.cgx_status:
        tenant_name = resp.cgx_content.get("name", None)
        print_array.append({ style: B0, data: pBold("Tenant Name") + ": " + pUnderline(tenant_name)  })
    else:
        logout()
        print_array.append({ style: B0, data: pFail("ERROR") + ": " + pUnderline("API Call failure when enumerating TENANT Name! Exiting!")  })
        print(resp.cgx_status)
        sys.exit((vars(resp)))
    uprint(print_array)

    site_count = 0
    search_site = CLIARGS['site_name']
    search_ratio = 0
    site_name = ""
    site_id = ""
    #########   END: TENANT INFORMATION  #########
    
    #########   START: SITE MATCH  #########
    print_array.clear()
    print_array.append({ style: P1, data: "SITE Information"})
    resp = cgx_session.get.sites()
    if resp.cgx_status:
        site_list = resp.cgx_content.get("items", None)    #EVENT_LIST contains an list of all returned events
        for site in site_list:                            #Loop through each EVENT in the EVENT_LIST
            check_ratio = fuzz.ratio(search_site.lower(),site['name'].lower())
            if (check_ratio > search_ratio ):
                site_id = site['id']
                site_name = site['name']
                search_ratio = check_ratio
                site_dict = site
    else:
        logout()
        print_array.append({ style: B0, data: pFail("ERROR") + ": " + pUnderline("API Call failure when enumerating SITES in tenant! Exiting!")  })
        uprint(print_array)
        sys.exit((jd(resp)))
    print_array.append({ style: T1, theader: "Health Check for SITE: '" + pUnderline(pBold(site_name)), data: [ [ "Site ID" , site_dict['id'] ],
                                                                                                                [ "Status"  , site_dict["admin_state"] ],
                                                                                                                [ "Description"  , site_dict["description"] ],
                                                                                                                [ "Address"  , site_dict["address"]["street"] + ", " + site_dict["address"]["city"] +  " " + site_dict["address"]["state"] +   ", " + site_dict["address"]["post_code"]  ],
                                                                                                                [ "Role"  , site_dict["element_cluster_role"] ],
                                                                                                              ]   })
    uprint(print_array)
    #########   END: SITE INFORMATION  #########
    
    #########   START: ELEMENT INFORMATION  #########
    print_array.clear()
    print_array.append({ style: P1, data: "ELEMENT Information"})
    site_elements = []
    ion_print_array = []
    element_count = 0
    resp = cgx_session.get.elements()
    if resp.cgx_status:
        print_array.append({ style: H1, data: "ION Status for site"})
        element_list = resp.cgx_content.get("items", None)    #EVENT_LIST contains an list of all returned events
        if (len(element_list) >= 0):
            for element in element_list:                            #Loop through each EVENT in the EVENT_LIST
                if (element['site_id'] == site_id):
                    element_count += 1
                    site_elements.append(element['id'])
                    if (element['connected'] == True):
                        ion_status = pPass("CONNECTED")
                    else:
                        ion_status = pFail("OFFLINE")
                    print_array.append({ style: T1, theader: "ION: " + pUnderline(element['name']), data: [ [ "Element ID" , element['id'] ],
                                                                                                                [ "Status"  , ion_status ],
                                                                                                              ]   })
        if (element_count == 0):
            print_array.append({ style: B1, data: "No IONS for site found"})
        uprint(print_array)
    #########   END: ELEMENT INFORMATION  #########
    
    #########   START: ALARMS INFORMATION  #########
    ### Get last 5 ALARMS for last diff_hours hours
    print_array.clear()
    print_array.append({ style: P1, data: "ALARMS Information"})

    dt_now = str(datetime.now().isoformat())
    dt_start = str((datetime.today() - timedelta(hours=diff_hours)).isoformat())
    dt_yesterday = str((datetime.today() - timedelta(hours=48)).isoformat())
    
    event_filter = '{"limit":{"count":5,"sort_on":"time","sort_order":"descending"},"view":{"summary":false},"severity":[],"query":{"site":["' + site_id + '"],"category":[],"code":[],"correlation_id":[],"type":["alarm"]}, "start_time": "' + dt_start + '", "end_time": "'+ dt_now + '"}'
    resp = cgx_session.post.events_query(event_filter)
    if resp.cgx_status:
        print_array.append( { style: H1, data: "Last 5 ALARMS for site within the past " + str(diff_hours) + " hours"} )
        alarms_list = resp.cgx_content.get("items", None)
        if(len(alarms_list) == 0 ):
            print_array.append( { style: B1, data: "No ALARMS found in time period" } )
        else:
            for alarm in alarms_list:
                if ( str(alarm['cleared']) == "True") :
                    acknowledged = pPass(str(alarm['cleared']))
                else:
                    acknowledged = pFail(str(alarm['cleared']))
                ###Color code Severity
                if (alarm['severity'] == "minor"):
                    severity = pWarn(str(alarm['severity']))
                elif (alarm['severity'] == "major"):
                    severity = pFail(str(alarm['severity']))
                else:
                    severity = pPass(str(alarm['severity']))
                print_array.append({ style: T1, theader: "ALARM: " + pUnderline(str(alarm['code'])), data:[ [ "Timestamp" , str(alarm['time']) ],
                                                                                                            [ "Severity"  , severity ],
                                                                                                            [ "Acknowledged"  , acknowledged ],
                                                                                                              ]   })
    else:
        print_array.append({ style: B1, data: pFail("ERROR in SCRIPT. Could not get ALARMS") })

    ### Get SUMMARY ALARMS  for last diff_hours hours
    alarm_summary_dict = {}
    event_filter = '{"limit":{"count":1000,"sort_on":"time","sort_order":"descending"},"view":{"summary":false},"severity":[],"query":{"site":["' + site_id + '"],"category":[],"code":[],"correlation_id":[],"type":["alarm"]}, "start_time": "' + dt_start + '", "end_time": "'+ dt_now + '"}'
    resp = cgx_session.post.events_query(event_filter)
    if resp.cgx_status:
        print_array.append({ style: H1, data: "ALARM Summaries for the past "+ str(diff_hours) + " hours"})
        alarms_list = resp.cgx_content.get("items", None)
        if(len(alarms_list) > 0 ):
            for alarm in alarms_list:
               if(alarm['code'] in alarm_summary_dict.keys() ):
                   alarm_summary_dict[alarm['code']] += 1
               else:
                   alarm_summary_dict[alarm['code']] = 1
            for alarm_code in alarm_summary_dict.keys():
                print_array.append({ style: B1, data: "Summaries for ALARM: " + pUnderline( str(alarm_code) ) })
                print_array.append({ style: B1, data: "              Count: " + pUnderline(str(alarm_summary_dict[alarm_code])) })
                print_array.append({ style: B1, data: " " })
                
        else:
            print_array.append({ style: B1, data: "No ALARM summaries found" })
    else:
        print_array.append({ style: B1, data: pFail("ERROR in SCRIPT. Could not get ALARM SUMMARIES") })
    uprint(print_array)
    #########   END: ALARMS INFORMATION  #########
    
    #########   START: ALERTS INFORMATION  #########
    ### Get last 5 ALERTS for last diff_hours hours
    print_array.clear()
    print_array.append({ style: P1, data: "ALERTS Information"})
    event_filter = '{"limit":{"count":5,"sort_on":"time","sort_order":"descending"},"view":{"summary":false},"severity":[],"query":{"site":["' + site_id + '"],"category":[],"code":[],"correlation_id":[],"type":["alert"]}, "start_time": "' + dt_start + '", "end_time": "'+ dt_now + '"}'
    resp = cgx_session.post.events_query(event_filter)
    if resp.cgx_status:
        print_array.append( { style: H1, data: "Last 5 ALERTS for site within the past " + str(diff_hours) + " hours"} )
        alerts_list = resp.cgx_content.get("items", None)
        if(len(alerts_list) == 0 ):
            print_array.append( { style: B1, data: "No ALERTS found in time period" } )
        else:
            alert_array_data = []
            for alert in alerts_list:
                alert_array_data.clear()
                if ( 'reason' in alert['info'].keys()):
                    alert_array_data.append( [  "Reason", str(alert['info']['reason'])  ]  )
                if ( 'process_name' in alert['info'].keys()):
                    alert_array_data.append( [  "Process", str(alert['info']['process_name'])  ]  )
                if ( 'detail' in alert['info'].keys()):
                    alert_array_data.append( [  "Details", str(alert['info']['detail'])  ]  )
                
                ##severity color coding
                if (alert['severity'] == "minor"):
                    alert_severity = pWarn(str(alert['severity']))
                elif (alert['severity'] == "major"):
                    alert_severity = pFail(str(alert['severity']))
                else:
                    alert_severity = pPass(str(alert['severity']))
                    
                alert_array_data.append( [  "Severity", alert_severity  ]  )
                alert_array_data.append( [  "Timestamp", str(alert['time'])  ]  )
                
                print_array.append({ style: T1, theader: "ALARM: " + pUnderline(str(alert['code'])), data:[ alert_array_data ]   })
    else:
        print_array.append({ style: B1, data: pFail("ERROR in SCRIPT. Could not get ALERTS") })

    ### Get ALERTS summary for last diff_hours hours
    alert_summary_dict = {}
    event_filter = '{"limit":{"count":1000,"sort_on":"time","sort_order":"descending"},"view":{"summary":false},"severity":[],"query":{"site":["' + site_id + '"],"category":[],"code":[],"correlation_id":[],"type":["alert"]}, "start_time": "' + dt_start + '", "end_time": "'+ dt_now + '"}'
    resp = cgx_session.post.events_query(event_filter)
    if resp.cgx_status:
        print_array.append({ style: H1, data: "ALERT Summaries for the past "+ str(diff_hours) + " hours"})
        alerts_list = resp.cgx_content.get("items", None)
        if(len(alerts_list) > 0 ):
            for alert in alerts_list:
               if(alert['code'] in alert_summary_dict.keys() ):
                   alert_summary_dict[alert['code']] += 1
               else:
                   alert_summary_dict[alert['code']] = 1
            for alert_code in alert_summary_dict.keys():
                print_array.append({ style: B1, data: "Summaries for ALARM: " + pUnderline( str(alert_code) ) })
                print_array.append({ style: B1, data: "              Count: " + pUnderline(str(alert_summary_dict[alert_code])) })
                print_array.append({ style: B1, data: " " })
        else:
            print_array.append({ style: B1, data: "No ALERT summaries found" })
    else:
        print_array.append({ style: B1, data: pFail("ERROR in SCRIPT. Could not get ALERT SUMMARIES") })
    uprint(print_array)
    #########   END: ALERTS INFORMATION  #########

    ###Generate NAME ID MAPS
    elements_id_to_name = idname.generate_elements_map()
    site_id_to_name = idname.generate_sites_map()
    wan_label_id_to_name = idname.generate_waninterfacelabels_map()
    wan_if_id_to_name = idname.generate_waninterfaces_map()
    
    wan_interfaces_resp = cgx_session.get.waninterfaces(site_id)
    wan_interfaces_list = wan_interfaces_resp.cgx_content.get("items")

    #########   START: VPN LINK INFORMATION  #########
    print_array.clear()
    print_array.append({ style: P1, data: "VPN Status"})
    topology_filter = '{"type":"basenet","nodes":["' +  site_id + '"]}'
    resp = cgx_session.post.topology(topology_filter)
    if resp.cgx_status:
        topology_list = resp.cgx_content.get("links", None)
        vpn_count = 0 
        for links in topology_list:
            if ((links['type'] == 'vpn') and links['source_site_name'] == site_name):
                vpn_count += 1
                vpn_text = "VPN " + str(vpn_count) + "-> SITE:" + site_name + " [ION:" + elements_id_to_name[links['source_node_id']]
                vpn_text += "]" + " ---> "+  wan_if_id_to_name[links['source_wan_if_id']] + ":" + links['source_wan_network'] + " " 
                vpn_text += pBold("---+--- ") + links['target_wan_network'] + ":"
                vpn_text += wan_if_id_to_name[links['target_wan_if_id']] + " <--- [" +  elements_id_to_name[links['target_node_id']]
                vpn_text += "] " + links['target_site_name']
                print_array.append({ style: H1, data: vpn_text } )
                if (links['status'] == "up"):
                    print_array.append({ style: B1, data: "STATUS: " + pPass("UP") })
                else:
                    print_array.append({ style: B1, data: "STATUS: " + pFail("DOWN") })

                if(('in_use' in links.keys()) and (links['in_use'])):
                    print_array.append({ style: B1, data: "USAGE : " + pPass("IN USE") })
                else:
                    print_array.append({ style: B1, data: "USAGE : " + pWarn("INACTIVE") })
                
                ###TODO add JITTER LATENCY PACKET-LOSS MEASUREMENTS HERE
        if (vpn_count == 0):
            print_array.append({ style: B1, data: "No SDWAN VPN links found at site" })
        uprint(print_array)
        #########   END: VPN LINK INFORMATION  #########
        
        #########   START: INTERNET PHYSICAL LINK INFORMATION  #########
        print_array.clear()
        print_array.append({ style: P1, data: "PHYSICAL LINK Status"})
        pcm_metrics_array_up = []  
        pcm_metrics_array_down = []          
        stub_count = 0
        for links in topology_list:
            if ((links['type'] == 'internet-stub') ):
                stub_count += 1
                if ('target_circuit_name' in links.keys()):
                    print_array.append({ style: H1, data: "Physical LINK: " + pBold(str(links['network'])) + ":" + pUnderline(str(links['target_circuit_name'])) })
                else:
                    print_array.append({ style: H1, data: "Physical LINK: " + pBold(str(links['network'])) })
                if (links['status'] == "up"):
                    print_array.append({ style: B1, data: "STATUS: " + pPass("UP") })
                elif (links['status'] == "init"):
                    print_array.append({ style: B1, data: "STATUS: " + pWarn("INIT") })
                else:
                    print_array.append({ style: B1, data: "STATUS: " + pFail("DOWN") })

                ### PCM PHY BANDWIDTH CAPACITY MEASUREMENTS
                pcm_request = '{"start_time":"'+ dt_start + 'Z","end_time":"' + dt_now + 'Z","interval":"5min","view":{"summary":false,"individual":"direction"},"filter":{"site":["' + site_id + '"],"path":["' + links['path_id'] + '"]},"metrics":[{"name":"PathCapacity","statistics":["average"],"unit":"Mbps"}]}'
                pcm_resp = cgx_session.post.metrics_monitor(pcm_request)
                pcm_metrics_array_up.clear()
                pcm_metrics_array_down.clear()
                measurements_up = 0
                measurements_down = 0
                z_count_down = 0
                z_count_up = 0
                if pcm_resp.cgx_status:
                    pcm_metric = pcm_resp.cgx_content.get("metrics", None)[0]['series']
                    if pcm_metric[0]['view']['direction'] == 'Ingress':
                        direction = "Download"
                    for series in pcm_metric:
                        if direction == "Download":                            
                            for datapoint in series['data'][0]['datapoints']:
                                if (datapoint['value'] == None):
                                    #pcm_metrics_array_down.append(0) ###IGNORE VALUES which are explicitly ZERO as it means no data - Per Aaron
                                    z_count_down += 1
                                else:
                                    pcm_metrics_array_down.append(datapoint['value'])
                                    measurements_down += 1
                            direction = 'Upload'
                        else:
                            for datapoint in series['data'][0]['datapoints']:                                
                                if (datapoint['value'] == None):
                                    #pcm_metrics_array_down.append(0) ###IGNORE VALUES which are explicitly ZERO as it means no data - Per Aaron
                                    z_count_up += 1
                                else:
                                    pcm_metrics_array_up.append(datapoint['value'])
                                    measurements_up += 1
                            direction = 'Download'

                    for wan_int in wan_interfaces_list:
                        if wan_int['id'] == links['path_id']:
                            upload = wan_int['link_bw_up']
                            download = wan_int['link_bw_down']
                            print_array.append({ style: T1, theader: "Configured Bandwidth/Throughput for the site", data:[ 
                                                                                                            [ "Maximum BW Download" , str(wan_int['link_bw_down']) ],
                                                                                                            [ "Maximum BW Upload" , str(wan_int['link_bw_up'])   ],
                                                                                                                            ]   })
                    error_percentage = 0.1
                    warn_percentage = 0.05
                    print_array.append({ style: H2, data: "THRESHOLDS: "+ pFail("RED") + ">=" + (str(error_percentage*100)) + "% |  "+pWarn("YELLOW") + ">=" + (str(warn_percentage*100)) + "%  | "+ pPass("GREEN") + "=Within " + (str(warn_percentage*100)) + "% | " + pExceptional("BLUE") + "="+ (str(error_percentage*100*2)) + "% Above expected" })
                    
                    print_array.append({ style: H2, data: "Measured Link Capacity (PCM) STATS for the last 24 hours" })
                    
                    if (len(pcm_metrics_array_up) == 0):
                        pcm_metrics_array_up.append(0)
                    if (len(pcm_metrics_array_down) == 0):
                        pcm_metrics_array_down.append(0)
                    
                    np_array = np.array(pcm_metrics_array_up)
                    print_array.append({ style: T1, theader: "Upload - Calculated from " + str(len(pcm_metrics_array_up)) + " Measurements in the past 24 Hours in mbits", data:[ 
                        [ "25th percentile",        metric_classifier( round(np.percentile(np_array,25),3),upload,error_percentage,warn_percentage) ],
                        ["50th Percentile(AVG)",    metric_classifier( round(np.average(np_array),3),upload,error_percentage,warn_percentage)       ],
                        ["75th percentile"     ,    metric_classifier( round(np.percentile(np_array,75),3),upload,error_percentage,warn_percentage) ],
                        ["95th percentile"      ,   metric_classifier( round(np.percentile(np_array,95),3),upload,error_percentage,warn_percentage) ],
                        ["Max Value"        ,       metric_classifier( round(np.amax(np_array),3),upload,error_percentage,warn_percentage)          ],
                                                ] })
                    
                    np_array = np.array(pcm_metrics_array_down)
                    print_array.append({ style: T1, theader: "Download - Calculated from " + str(len(pcm_metrics_array_down)) + " Measurements in the past 24 Hours in mbits", data:[ 
                        [ "25th percentile",        metric_classifier( round(np.percentile(np_array,25),3),download,error_percentage,warn_percentage) ],
                        ["50th Percentile(AVG)",    metric_classifier( round(np.average(np_array),3),download,error_percentage,warn_percentage)       ],
                        ["75th percentile"     ,    metric_classifier( round(np.percentile(np_array,75),3),download,error_percentage,warn_percentage) ],
                        ["95th percentile"      ,   metric_classifier( round(np.percentile(np_array,95),3),download,error_percentage,warn_percentage) ],
                        ["Max Value"        ,       metric_classifier( round(np.amax(np_array),3),download,error_percentage,warn_percentage)          ],
                                                ] })
        if (stub_count == 0):
            print_array.append({ style: H2, data: "No Physical links found at site" })
        uprint(print_array)
        #########   END: INTERNET PHYSICAL LINK INFORMATION  #########

        #########   START: Private-ANYNET PWAN LINK INFORMATION  #########
        print_array.clear()
        print_array.append({ style: P1, data: "Private-WAN LINK Status"})
        pcm_metrics_array_up = []  
        pcm_metrics_array_down = []    
        pwan_interfaces_completed = []      
        stub_count = 0
        for links in topology_list:
            if ((links['type'] == 'private-anynet') and (links['target_circuit_name'] not in pwan_interfaces_completed) and (links['source_circuit_name'] not in pwan_interfaces_completed) ):
                stub_count += 1
                if (links['target_site_name'] == site_name):
                    pwan_print_data = "PrivateWAN LINK: " + pBold(str(links['target_circuit_name'])) + " (" + pUnderline(str(links['target_wan_network'])) + ")" 
                    pwan_link_filter = links['target_wan_if_id']
                    pwan_interfaces_completed.append(links['target_circuit_name'])
                else:
                     
                    pwan_print_data = "PrivateWAN LINK: " + pBold(str(links['source_circuit_name'])) + " (" + pUnderline(str(links['source_wan_network'])) + ")" 
                    pwan_link_filter = links['source_wan_if_id']
                    pwan_interfaces_completed.append(links['source_circuit_name'])

                print_array.append({ style: H1, data:  pwan_print_data  })
                
                if (links['status'] == "up"):
                    print_array.append({ style: B1, data: "STATUS: " + pPass("UP") })
                elif (links['status'] == "init"):
                    print_array.append({ style: B1, data: "STATUS: " + pWarn("INIT") })
                else:
                    print_array.append({ style: B1, data: "STATUS: " + pFail("DOWN") })

                ### PCM PHY BANDWIDTH CAPACITY MEASUREMENTS
                pcm_request = '{"start_time":"'+ dt_start + 'Z","end_time":"' + dt_now + 'Z","interval":"5min","view":{"summary":false,"individual":"direction"},"filter":{"site":["' + site_id + '"],"path":["' + pwan_link_filter + '"]},"metrics":[{"name":"PathCapacity","statistics":["average"],"unit":"Mbps"}]}'
                pcm_resp = cgx_session.post.metrics_monitor(pcm_request)
                pcm_metrics_array_up.clear()
                pcm_metrics_array_down.clear()
                measurements_up = 0
                measurements_down = 0
                z_count_down = 0
                z_count_up = 0
                if pcm_resp.cgx_status:
                    pcm_metric = pcm_resp.cgx_content.get("metrics", None)[0]['series']
                    if pcm_metric[0]['view']['direction'] == 'Ingress':
                        direction = "Download"
                    for series in pcm_metric:
                        if direction == "Download":                            
                            for datapoint in series['data'][0]['datapoints']:
                                if (datapoint['value'] == None):
                                    #pcm_metrics_array_down.append(0) ###IGNORE VALUES which are explicitly ZERO as it means no data - Per Aaron
                                    z_count_down += 1
                                else:
                                    pcm_metrics_array_down.append(datapoint['value'])
                                    measurements_down += 1
                            direction = 'Upload'
                        else:
                            for datapoint in series['data'][0]['datapoints']:                                
                                if (datapoint['value'] == None):
                                    #pcm_metrics_array_down.append(0) ###IGNORE VALUES which are explicitly ZERO as it means no data - Per Aaron
                                    z_count_up += 1
                                else:
                                    pcm_metrics_array_up.append(datapoint['value'])
                                    measurements_up += 1
                            direction = 'Download'

                    for wan_int in wan_interfaces_list:
                        if wan_int['id'] == pwan_link_filter: #links['path_id']:
                            upload = wan_int['link_bw_up']
                            download = wan_int['link_bw_down']
                            print_array.append({ style: T1, theader: "Configured Bandwidth/Throughput for the site", data:[ 
                                                                                                            [ "Maximum BW Download" , str(wan_int['link_bw_down']) ],
                                                                                                            [ "Maximum BW Upload" , str(wan_int['link_bw_up'])   ],
                                                                                                                            ]   })
                    error_percentage = 0.1
                    warn_percentage = 0.05
                    print_array.append({ style: H2, data: "THRESHOLDS: "+ pFail("RED") + ">=" + (str(error_percentage*100)) + "% |  "+pWarn("YELLOW") + ">=" + (str(warn_percentage*100)) + "%  | "+ pPass("GREEN") + "=Within " + (str(warn_percentage*100)) + "% | " + pExceptional("BLUE") + "="+ (str(error_percentage*100*2)) + "% Above expected" })
                    
                    print_array.append({ style: H2, data: "Measured Link Capacity (PCM) STATS for the last 24 hours" })
                    
                    if (len(pcm_metrics_array_up) == 0):
                        pcm_metrics_array_up.append(0)
                    if (len(pcm_metrics_array_down) == 0):
                        pcm_metrics_array_down.append(0)
                    
                    np_array = np.array(pcm_metrics_array_up)
                    print_array.append({ style: T1, theader: "Upload - Calculated from " + str(len(pcm_metrics_array_up)) + " Measurements in the past 24 Hours in mbits", data:[ 
                        [ "25th percentile",        metric_classifier( round(np.percentile(np_array,25),3),upload,error_percentage,warn_percentage) ],
                        ["50th Percentile(AVG)",    metric_classifier( round(np.average(np_array),3),upload,error_percentage,warn_percentage)       ],
                        ["75th percentile"     ,    metric_classifier( round(np.percentile(np_array,75),3),upload,error_percentage,warn_percentage) ],
                        ["95th percentile"      ,   metric_classifier( round(np.percentile(np_array,95),3),upload,error_percentage,warn_percentage) ],
                        ["Max Value"        ,       metric_classifier( round(np.amax(np_array),3),upload,error_percentage,warn_percentage)          ],
                                                ] })
                    
                    np_array = np.array(pcm_metrics_array_down)
                    print_array.append({ style: T1, theader: "Download - Calculated from " + str(len(pcm_metrics_array_down)) + " Measurements in the past 24 Hours in mbits", data:[ 
                        [ "25th percentile",        metric_classifier( round(np.percentile(np_array,25),3),download,error_percentage,warn_percentage) ],
                        ["50th Percentile(AVG)",    metric_classifier( round(np.average(np_array),3),download,error_percentage,warn_percentage)       ],
                        ["75th percentile"     ,    metric_classifier( round(np.percentile(np_array,75),3),download,error_percentage,warn_percentage) ],
                        ["95th percentile"      ,   metric_classifier( round(np.percentile(np_array,95),3),download,error_percentage,warn_percentage) ],
                        ["Max Value"        ,       metric_classifier( round(np.amax(np_array),3),download,error_percentage,warn_percentage)          ],
                                                ] })
                    print_array.append({ style: B0, data: " " })
            
        if (stub_count == 0):
            print_array.append({ style: H2, data: "No Private-WAN links found at site" })
        uprint(print_array)
        #########   END: Private-ANYNET PHYSICAL LINK INFORMATION  #########
        
        #########   START: 3rd party VPN LINK INFORMATION  #########
        print_array.clear()
        print_array.append({ style: P1, data: "3rd Party VPN Link Status"})
        service_link_count = 0
        for links in topology_list:
            if ((links['type'] == 'servicelink')):
                service_link_count += 1
                if (links['status'] == "up"):
                    print_array.append({ style: T1, theader: "3RD PARTY LINK: " + pBold(str(links['sep_name'])) + " VIA WAN " + pUnderline(str(links['wan_nw_name'])) , data:   [   ["STATUS", pPass("UP")]  ] })
                else:
                    print_array.append({ style: T1, theader: "3RD PARTY LINK: " + pBold(str(links['sep_name'])) + " VIA WAN " + pUnderline(str(links['wan_nw_name'])) , data:   [   ["STATUS", pFail("DOWN")]  ] })
        if (service_link_count == 0):
            print_array.append({ style: B1, data: "No 3rd party VPN tunnels found"})
        uprint(print_array)
        #########   START: 3rd party VPN LINK INFORMATION  #########
        
    #########   START: DNS RESPONSE TIME  #########
    print_array.clear()
    print_array.append({ style: P1, data: "DNS Response Time Metrics (TRT)"})
    app_name_map = {}    
    app_name_map = idname.generate_appdefs_map(key_val="display_name", value_val="id")
    if ("dns" in app_name_map.keys()):
        dns_app_id = app_name_map['dns']   
        dns_request = '{"start_time":"' + dt_start + 'Z","end_time":"'+ dt_now + 'Z","interval":"5min","metrics":[{"name":"AppUDPTransactionResponseTime","statistics":["average"],"unit":"milliseconds"}],"view":{},"filter":{"site":["' + site_id + '"],"app":["' + dns_app_id + '"],"path_type":["DirectInternet","VPN","PrivateVPN","PrivateWAN","ServiceLink"]}}'
        dns_trt_array = []
        resp = cgx_session.post.metrics_monitor(dns_request)
        if resp.cgx_status:
            dns_metrics = resp.cgx_content.get("metrics", None)[0]['series'][0]
            for datapoint in dns_metrics['data'][0]['datapoints']:
                if (datapoint['value'] == None):
                    dns_trt_array.append(0)
                else:
                    dns_trt_array.append(datapoint['value'])
            
            np_array = np.array(dns_trt_array)
            
            print_array.append({ style: T1, theader: "DNS TRT Stats for the past 24 Hours (in milliseconds)", data:[ 
                        ["Minimum",                 dns_trt_classifier( round(np.amin(np_array),2)) ],
                        ["Average",                 dns_trt_classifier( round(np.average(np_array),2))       ],
                        ["80th percentile"     ,    dns_trt_classifier( round(np.percentile(np_array,80),2)) ],
                        ["95th percentile"      ,   dns_trt_classifier( round(np.percentile(np_array,95),2)) ],
                        ["Max Value"        ,       dns_trt_classifier( round(np.amax(np_array),2))          ],
                                                ] })


            ### Get stats from 48 hours ago
            dns_request = '{"start_time":"' + dt_yesterday + 'Z","end_time":"'+ dt_start + 'Z","interval":"5min","metrics":[{"name":"AppUDPTransactionResponseTime","statistics":["average"],"unit":"milliseconds"}],"view":{},"filter":{"site":["' + site_id + '"],"app":["' + dns_app_id + '"],"path_type":["DirectInternet","VPN","PrivateVPN","PrivateWAN","ServiceLink"]}}'
            dns_trt_array.clear()
            resp = cgx_session.post.metrics_monitor(dns_request)
            dns_metrics = resp.cgx_content.get("metrics", None)[0]['series'][0]
            for datapoint in dns_metrics['data'][0]['datapoints']:
                if (datapoint['value'] == None):
                    dns_trt_array.append(0)
                else:
                    dns_trt_array.append(datapoint['value'])
            np_array_yesterday = np.array(dns_trt_array)
            
            print_array.append({ style: T1, theader: "DNS TRT Stats from Yesterday (in milliseconds)", data: [ 
                        ["Minimum",                 dns_trt_classifier( round(np.amin(np_array_yesterday),2)) ],
                        ["Average",                 dns_trt_classifier( round(np.average(np_array_yesterday),2))       ],
                        ["80th percentile"     ,    dns_trt_classifier( round(np.percentile(np_array_yesterday,80),2)) ],
                        ["95th percentile"      ,   dns_trt_classifier( round(np.percentile(np_array_yesterday,95),2)) ],
                        ["Max Value"        ,       dns_trt_classifier( round(np.amax(np_array_yesterday),2))          ],
                                                ] })
            

    else:
        print_array.append({ style: B1, data: pFail("ERROR") + " Could not retrieve DNS TRT STATS"})
    uprint(print_array)
    #########   END: DNS RESPONSE TIME  #########
    
    #########   START: Get Palo Alto Prisma Status  #########
    print_array.clear()
    print_array.append({ style: P1, data: "Palo Alto Networks Cloud Status}"})
    pan_core_services_url = 'https://status.paloaltonetworks.com/'
    pan_health_request = requests.get(url = pan_core_services_url)
    pan_tree_data = html.fromstring(pan_health_request.content)
    pan_svc_array = []
    
    for service in pan_service_dict:
        service_status = getpanstatus(pan_tree_data, pan_service_dict[service] )
        if (service_status == "Operational"):
            pan_svc_array.append([ service , pPass(service_status) ])
        else:
            pan_svc_array.append([ service , pFail(service_status) ])
    if (len(pan_svc_array) >= 1):
        pan_svc_array.insert(0, [pUnderline("SERVICE"),pUnderline("STATUS")] )
        print_array.append({ style: T1, theader: "Palo Alto Prisma Cloud STATUS from: " + pUnderline(pan_core_services_url), data: pan_svc_array })
    else:
        print_array.append({ style: B1, data:  "No Palo Alto Services Found" })
    uprint(print_array)
    #########   END: Get Palo Alto Prisma Status  #########
    
    #########   START: Get zScaler Cloud Status  #########
    print_array.clear()
    print_array.append({ style: P1, data: "zScaler ZEN Cloud Status"})
    zs_core_services_url = 'https://trust.zscaler.com/api/cloud-status.json?_format=json&a=b'
    zs_post_data = '{"cloud":"trust.zscaler.net","dateOffset":0,"requestType":"core_cloud_services"}'
    zs_query_params = {'_format': 'json', 'a': 'b'}
    zs_headers =  {'Content-type': 'application/json'}
    zs_svc_array = []
    zscaler_health_request = requests.post(url = zs_core_services_url, data = zs_post_data, params=zs_query_params, headers=zs_headers)
    zs_data = zscaler_health_request.json()
    zscaler_severity = {}
    
    for severity in zs_data['data']['severity']:
        zscaler_severity[severity['tid']] = severity['name']

    if ('data' in zs_data.keys()):
        if ('category' in zs_data['data'].keys()):
            for service in zs_data['data']['category'][0]['subCategory']:
                if ('category_status' in service.keys()):
                    zs_svc_array.append(
                            [
                        service['name'], 
                        pFail(zscaler_severity[service['category_status']['severityTid']]) + ":" + service['category_status']['severityTid'], 
                        pBold(service['category_status']['short_description']).replace("&nbsp;"," ")  
                            ])
                else:
                    zs_svc_array.append([service['name'], pPass("GOOD") , " "])
    zs_svc_array.insert(0, [pUnderline("SERVICE"),pUnderline("STATUS"),pUnderline("DESCRIPTION")])
    print_array.append({ style: T1, theader: "zScaler Cloud STATUS from: " + pUnderline("https://trust.zscaler.com/cloud-status"), data: zs_svc_array })
    uprint(print_array)
    #########   END: Get zScaler Cloud Status  #########
    
    #########   START: Check MSFT Cloud Serivces status  #########
    print_array.clear()
    print_array.append({ style: P1, data: "Microsoft Cloud STATUS" })
    ms_core_services_url = 'https://portal.office.com/api/servicestatus/index'
    ms_svc_array = []
    ms_headers =  {'Content-type': 'application/json'}
    ms_health_request = requests.get(url = ms_core_services_url,  headers=ms_headers)
    ms_data = ms_health_request.json()

    if ('Services' in ms_data.keys()):
        for service in ms_data['Services']:
            if (service['IsUp']):
                ms_svc_array.append([service['Name'], pPass("GOOD")])
            else:
                ms_svc_array.append([service['Name'], pFail("ISSUE DETECTED")])
    if (len(ms_svc_array) >= 1):
        ms_svc_array.insert(0, [pUnderline("SERVICE"),pUnderline("STATUS")] )
        print_array.append({ style: T1, theader: "Microsoft Cloud STATUS from: " + pUnderline("https://portal.office.com/servicestatus"), data: ms_svc_array })
    else:
        print_array.append({ style: B1, data:  "ERROR: No Microsoft Cloud Services Found" })
    uprint(print_array)
    #########   END: Check MSFT Cloud Serivces status  #########
    
    #########   START: Check GOOGLE Cloud Serivces status  #########
    print_array.clear()
    print_array.append({ style: P1, data: "GOOGLE Cloud STATUS" })
    google_core_services_url = 'https://www.google.com/appsstatus/json/en'
    google_svc_array = []
    google_headers =  {'Content-type': 'application/json'}
    google_health_request = requests.get(url = google_core_services_url,  headers=google_headers)
    google_data = json.loads(google_health_request.text.replace("dashboard.jsonp(","").replace("});","}"))

    google_service_list = {}
    for service in google_data['services']:
        google_service_list[service['id']] = service['name']
    for messages in google_data['messages']:
        if (not(messages['resolved'])):            
            google_svc_array.append(   [  google_service_list[messages['service']], pFail("ISSUE DETECTED")  ])
    
    if (len(google_svc_array) >= 1):
        google_svc_array.insert(0, [pUnderline("SERVICE"),pUnderline("STATUS")] )
        print_array.append({ style: T1, theader: "GOOGLE Cloud STATUS from: " + pUnderline("https://portal.office.com/servicestatus"), data: google_svc_array })
    else:
        print_array.append({ style: B0, data:  pPass("GOOD") + ", No unresolved issues found!" })
    uprint(print_array)
    #########   END: Check GOOGLE Cloud Serivces status  #########
    return("DONE")

def logout():
    print("Logging out")
    cgx_session.get.logout()

if __name__ == "__main__":
    parse_arguments()
    authenticate()
    go()
    logout()
