#!/usr/bin/env python3
"""Extract doc strings from monitor plugins and build the overall lanmonitor README.md
"""

#==========================================================
#
#  Chris Nelson, 2024
#
#==========================================================

import pathlib
# import re
import shutil
import sys
import importlib.util
from cjnfuncs.mungePath import mungePath

PART1 =         'lanmonitor_P1.md'
PART2 =         'lanmonitor_P2.md'
PART3 =         'lanmonitor_P3.md'
SRC_PATH =      '../src/lanmonitor'
OUTFILE =       '../README.md'


plugin_modules = [
    {'module_name':'apt_upgrade_history_plugin',    'oneliner':"Checks that the most recent apt upgrade operation was more recent than a given age"},
    {'module_name':'dd_wrt_age_plugin',             'oneliner':"Checks that the dd-wrt version on the target router is more recent than a given age"},
    {'module_name':'freespace_plugin',              'oneliner':"Checks that the filesystem of the given path has a minimum of free space"},
    {'module_name':'fsactivity_plugin',             'oneliner':"Checks that a target file or directory has at least one file newer than a given age"},
    {'module_name':'interface_plugin',              'oneliner':"Checks that a given network interface (i.e., eth2) is up and running"},
    {'module_name':'pinghost_plugin',               'oneliner':"Checks that a given host can be pinged, as an indicator that the machine is alive on your network"},
    {'module_name':'process_plugin',                'oneliner':"Checks that a given process is alive on a target host"},
    {'module_name':'selinux_plugin',                'oneliner':"Checks that selinux reports the expected 'enforcing' or 'permissive'"},
    {'module_name':'service_plugin',                'oneliner':"Checks that the given init.d or systemd service reports that it's up and running"},
    {'module_name':'webpage_plugin',                'oneliner':"Checks that the given URL responds with an expected string of text, as an indicator that that the web page is alive"},
    {'module_name':'yum_update_history_plugin',     'oneliner':"Checks that the most recent yum update operation was more recent than a given age"},
    ]


def main():

    outfile = pathlib.Path(OUTFILE)


    # PART1 ======================================================
    print ("Copying PART1")
    shutil.copy(PART1, outfile)


    # Plugins table ======================================================
    print ("Producing plugins table")
    with outfile.open('a') as ofile:
        ofile.write(r"""
<br/>

---

## Several plugins are provided in the distribution (more details [below](#supplied-plugins)):

| Monitor plugin | Description |
|-----|-----|
""")

        for module in plugin_modules:
            ofile.write(f"{module['module_name']} | {module['oneliner']}\n")
            
        ofile.write(r"""
If you need other plug-ins, or wish to contribute, please open an issue on the github repo to discuss. 
See [Writing_New_Plugins](https://github.com/cjnaz/lanmonitor/blob/main/Writing_New_Plugins.md) 
for plugin implementation details.


""")


        # PART2 ======================================================
        print ("Appending PART2")

        def append_part (part):
            with open(part, 'r') as inpart:
                    shutil.copyfileobj(inpart, ofile)
                    
        append_part(PART2)


        # Plugin doc strings ======================================================
        print ("Extracting monitor plugin doc strings")


        ofile.write(r"""

<br/>

<a id="supplied-plugins"></a>

---

## Supplied plugins
""")

        def lazy_import(name):      # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
            spec = importlib.util.find_spec(name)
            loader = importlib.util.LazyLoader(spec.loader)
            spec.loader = loader
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            loader.exec_module(module)
            return module

        for module in plugin_modules:
            print (f"    plugin {module['module_name']}")
            plugin_mp = mungePath(module['module_name'] + '.py', SRC_PATH)

            plugin_parent = str(plugin_mp.parent)
            if plugin_parent not in sys.path:
                sys.path.append(plugin_parent)

            imported_module = lazy_import(module['module_name'])

### {module['module_name']}
            ofile.write(f"""{imported_module.__doc__}
<br/>

---
""")


        # PART3 ======================================================
        print ("Appending PART3")

        append_part(PART3)

        exit()

#     for module in modules:
#         print (f"Processing {module['outfile']}")
#         links       = build_links_list(module['source'])
#         docstrings  = extract_docstrings(module['source'])

#         with pathlib.Path(module['outfile']).open('w') as ofile:
#             ofile.write(pathlib.Path(module['head']).read_text())

#             ofile.write(r"""

# <a id="links"></a>
         
# <br>

# ---

# # Links to classes, methods, and functions

# """)
#             ofile.write(links)

#             ofile.write(r"""

# """)
#             ofile.write(docstrings)

# # Doc string format example:
# '''
# def snd_notif(subj="Notification message", msg="", to="NotifList", log=False):
#     """
# ## snd_notif (subj="Notification message, msg="", to="NotifList", log=False) - Send a text message using info from the config file
# (...documentation...)
#     """
# '''

# comment_block = re.compile(r'"""\s+##\s([\s\S]+?)(?:""")')

# def build_links_list(source):

#     all = pathlib.Path(source).read_text()
#     # Build the links list
#     links = ''
#     for block in comment_block.finditer(all):
#         link_name = get_linkname(block)
#         links += f"- [{link_name}](#{link_name})\n"
#     return links

#         # link = funcline.replace(" ", "-").lower()
#         # deleted = ":()\n,.=\"\'"
#         # for char in deleted:
#         #     link = link.replace(char, "")
#         # links += f"- [{link_name}](#{link})\n"


# def extract_docstrings(source):
#     xx = ''
#     all = pathlib.Path(source).read_text()

#     # xx += (links)

#     for block in comment_block.finditer(all):
#         link_name = get_linkname(block)
#         print (f"    Processing {link_name}")
#         xx += "\n<br/>\n\n"
#         xx += f'<a id="{link_name}"></a>\n\n'
#         xx += "---\n\n"
#         xx += "# " + block.group(1)

#     return xx


# def get_linkname(block):
#     funcline = block.group(1).split('\n')[0]
#     return funcline.replace("Class ", "").split(maxsplit=1)[0].lower()

if __name__ == '__main__':
    main()


