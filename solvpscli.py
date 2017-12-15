#!/usr/bin/env python3
import robobrowser
import webbrowser
import argparse
import getpass

p = argparse.ArgumentParser(description='''
This is a tool to manage SolVPS virtual private servers directly from the command line.

It works by scraping the web-based user interface at https://www.solvps.com/secure/clientarea.php
''')
p.add_argument('id', nargs='?', help="numeric ID or domain name of VPS")
p.add_argument('action', nargs='?', default='status', choices=('status','browse','boot','reboot','shutdown','ssh','rdp'), help="Action to perform on the VPS (ssh only for Linux, rdp only for Windows)")
p.add_argument('-u', '--username')
p.add_argument('-p', '--password')
args = p.parse_args()

br=robobrowser.RoboBrowser(parser='html.parser')

print("Logging in to SolVPS...")
br.open('https://www.solvps.com/secure/clientarea.php')
f = br.get_form(0)
f['username'] = args.username or input('Username: ')
f['password'] = args.password or getpass.getpass('Password: ')
br.submit_form(f)
if 'incorrect=true' in br.url:
    p.error('Incorrect username or password')

if args.id is None:
    # Parse ID, domain name, and description out of this HTML:
    #   <a menuItemName="0" href="/secure/clientarea.php?action=productdetails&id=12345" class="list-group-item" id="ClientAreaHomePagePanels-Active_Products_Services-0">
    #   Windows VPS - Custom Windows VPS<br /><span class="text-domain">xyzdomain</span></a>
    spans = br.find_all("span", {'class':'text-domain'})
    domain_id_desc = [(span.text, int(span.parent['href'].split('id=')[-1]), next(span.parent.stripped_strings, None)) for span in spans]
    print("No VPS ID or domain name specified. List:")
    for domain, vps_id, desc in domain_id_desc:
        print("%-6d) %s\n\t%s" % (vps_id, domain, desc))
    raise SystemExit
elif args.id.isdigit():
    vps_id = int(args.id)
else:
    span = br.find("span", {'class':'text-domain'}, text=args.id)
    if span is None:
        p.error("Couldn't find domain %s under your services" % args.id)

    try:
        vps_id = int(span.parent['href'].split('id=')[-1])
    except Exception:
        p.error("Found domain %s, but couldn't parse ID from:\n\t%s" % (args.id, span.parent))
    print("Found domain %s with VPS ID %d" % (args.id, vps_id))

if args.action in ('boot','shutdown','reboot'):
    br.open('https://www.solvps.com/secure/clientarea.php?action=productdetails&id=%d&mg-action=%sVM' % (vps_id, args.action))
    print(br.response.text)
elif args.action=='browse':
    webbrowser.open('https://www.solvps.com/secure/clientarea.php?action=productdetails&id=%d' % vps_id)
elif args.action=='status':
    br.open('https://www.solvps.com/secure/clientarea.php?action=productdetails&id=%d' % vps_id)
    tbl = br.find("table", {'class':'table pm-stats'})
    print("VM status:")
    for tr in tbl.find_all('tr'):
        tds = tr.find_all('td')
        print('\t%-20s : %s' % (tds[0].text, ' '.join(tds[1].stripped_strings)))
elif args.action=='ssh':
    br.open('https://www.solvps.com/secure/clientarea.php?action=productdetails&id=%d&mg-action=vnc' % vps_id)
    applet = br.find('applet')
    sshdest = applet and applet.find('param', {'name':'jcterm.destinations'})
    strongs = br.find_all('strong')
    if not sshdest or len(strongs)!=2:
        p.error("Couldn't parse console page (%s)" % br.url)

    console_host, console_port = sshdest['value'].split(':')
    console_password = strongs[1].text
    print("\n\tsshpass -p '%s' ssh %s%s\n" % (console_password, ('' if console_port=='22' else '-p%s ' % console_port), console_host))
elif args.action=='rdp':
    #br.open('https://www.solvps.com/secure/clientarea.php?action=productdetails&id=%d&mg-action=novnc' % vps_id)
    p.error("Not yet supported")
