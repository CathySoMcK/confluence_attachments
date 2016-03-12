#!/usr/bin/python
"""
Downloads all the attachments and page content from a Confluence space using XML-RPC API
Licence:  MIT
Python ver: 2.7
"""
__author__ = 'Emidio Stani, PwC EU Services'

import shutil
from datetime import datetime
import sys
import xmlrpclib
import StringIO
import os
import getopt


# References:
# https://jira.atlassian.com/browse/CONF-5669
# https://answers.atlassian.com/questions/114490/how-to-get-all-attachments-under-a-space-via-rest-api
# https://github.com/pycontribs/confluence/blob/master/confluence/confluence.py
# https://www.pythonanywhere.com/forums/topic/775/
# http://stackoverflow.com/questions/8024248/telling-python-to-save-a-txt-file-to-a-certain-directory-on-windows-and-mac
# https://developer.atlassian.com/download/attachments/5670198/CONFDEV-310811-0150-38.pdf?api=v2
# http://stackoverflow.com/questions/16204230/build-tree-out-of-list-of-parent-children-in-python
# http://stackoverflow.com/questions/10047643/how-to-create-dict-with-childrens-from-dict-with-parent-id
# http://stackoverflow.com/questions/15723630/python-search-for-and-delete-nested-lists-of-dictionaries
# https://answers.atlassian.com/questions/22485/retrieving-ready-to-render-html-of-a-page-via-xmlrpc
# http://stackoverflow.com/questions/9942594/unicodeencodeerror-ascii-codec-cant-encode-character-u-xa0-in-position-20

def main(argv):
    rpcurl = ''
    username = ''
    password = ''
    space = ''
    error_msg = 'Usage: python server.py -r <http(s)://x.y.z/confluence/rpc/xmlrpc> -u <username> -p <password> -s <space>'
    try:
        opts, args = getopt.getopt(argv, "hr:u:p:s:", ["rpcurl=", "user=", "pass=", "space="])
    except getopt.GetoptError:
        print error_msg
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print error_msg
            sys.exit()
        elif opt in ("-r", "--rpcurl"):
            rpcurl = arg
        elif opt in ("-u", "--user"):
            username = arg
        elif opt in ("-p", "--pass"):
            password = arg
        elif opt in ("-s", "--space"):
            space = arg

    print 'rpcurl is:', rpcurl
    print 'username is:', username
    print 'password is:', password
    print 'space is:', space
    if (rpcurl == '') or (username == '') or (password == '') or (space == ''):
        print error_msg
        sys.exit()

    start_time = datetime.now()
    print "Script starts:", start_time
    server = xmlrpclib.ServerProxy(rpcurl)
    token = server.confluence1.login(username, password)
    pagetree = server.confluence1.getPages(token, space)
    numpages = len(pagetree)
    print "There are ", numpages, " pages in ", space
    pagenum = 0
    allpages = []
    for pagedict in pagetree:
        pageid = pagedict['id']
        pagetitle = pagedict['title']
        folder = pagetitle.replace(':', "").replace('/', "")
        if not os.path.exists(folder):
            os.makedirs(folder)
        # print pageid
        pagecontent = server.confluence1.renderContent(token, space, pageid, '')
        wikipage = os.path.join(folder, folder+".html")
        text_file = open(wikipage, "w")
        text_file.write(pagecontent.encode('ascii', 'ignore').decode('ascii'))
        text_file.close()
        attachments = server.confluence1.getAttachments(token, pageid)
        # print attachments
        numattachments = len(attachments)
        for attach in attachments:
            data = server.confluence1.getAttachmentData(token, pageid, attach['title'], "0")
            filebinary = StringIO.StringIO(data)
            complete_name = os.path.join(folder, attach['title'].replace(':', ""))
            fileattachment = open(complete_name, "wb")
            fileattachment.write(filebinary.getvalue())
            fileattachment.close()
        pageparentid = pagedict['parentId']
        pageinfo = {'pageid': pageid, 'pagetitle': folder, 'pageparentid': pageparentid}
        allpages.append(pageinfo)
        pagenum += 1
        print "Downloaded page ", pagenum, "/", numpages, " with ", numattachments, " attachments"

    print "Moving folders..."
    cats_dict = dict((cat['pageid'], cat) for cat in allpages)
    for cat in allpages:
        if cat['pageparentid'] != "0":
            parent = cats_dict[cat['pageparentid']]
            parent.setdefault('children', []).append(cat)

    allpages = [cat for cat in allpages if cat['pageparentid'] == "0"]
    # print allpages

    def walk(node, parent=None, func=None):
        for child in list(node.get('children', [])):
            walk(child, parent=node, func=func)
        if func is not None:
            func(node, parent=parent)

    def move_folders(node, parent):
        if node['pageparentid'] != "0":
            shutil.move(node['pagetitle'], parent['pagetitle'])

    for cat in allpages:
        # print cat['pageid']
        walk(cat, func=move_folders)

    end_time = datetime.now()
    print "Script end:", end_time
    print "Total time:", end_time - start_time
    exit('Done!')

if __name__ == "__main__":
    main(sys.argv[1:])
