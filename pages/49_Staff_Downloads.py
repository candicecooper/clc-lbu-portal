"""
Staff Downloads
----------------
A simple, always-open reference page linking staff straight to the official
download/install pages for the firmware, apps and software used on CLC-LBU
devices (e.g. setting up a brand-new laptop or replacement device).

No database needed — this list is just a Python dict below. To add, edit or
remove a link: open this file in GitHub, edit the DOWNLOADS dict, commit.
No admin panel, no Supabase table, nothing to break.
"""

import streamlit as st

st.set_page_config(page_title="Staff Downloads", page_icon="⬇️", layout="wide")

# --------------------------------------------------------------------------
# EDIT THIS SECTION TO ADD / CHANGE LINKS
# Each category is a list of items: name, short description, and the URL to
# send staff to. Prefer the official vendor/download page over a direct file
# link, since those break when a version updates.
# --------------------------------------------------------------------------
DOWNLOADS = {
    "New device setup": [
        {
            "name": "Windows Update (firmware & drivers)",
            "desc": "Most device firmware (BIOS, chipset, touchpad, camera) is delivered "
                    "through Windows Update, not a separate download. Settings → Windows "
                    "Update → Check for updates, then Advanced options → Optional updates.",
            "url": "ms-settings:windowsupdate",
        },
        {
            "name": "Manufacturer support & drivers page",
            "desc": "If a driver isn't showing in Windows Update, go to the manufacturer's "
                    "support site and search the device's model/serial number.",
            "url": "https://support.hp.com/au-en/drivers",
        },
    ],
    "Core apps": [
        {
            "name": "Microsoft Teams",
            "desc": "Chat, calls, meetings.",
            "url": "https://www.microsoft.com/en-au/microsoft-teams/download-app",
        },
        {
            "name": "Microsoft 365 apps (Word, Excel, Outlook, PowerPoint)",
            "desc": "Install or reinstall the full Office suite.",
            "url": "https://www.office.com/?auth=2",
        },
        {
            "name": "OneDrive",
            "desc": "File sync client — usually bundled with Windows but can be reinstalled here.",
            "url": "https://www.microsoft.com/en-au/microsoft-365/onedrive/download",
        },
    ],
    "Department for Education systems": [
        {
            "name": "DfE Self Service Portal",
            "desc": "Department software catalogue — install approved DfE applications.",
            "url": "https://www.education.sa.gov.au",
        },
    ],
    "Browsers & PDF": [
        {
            "name": "Google Chrome",
            "desc": "",
            "url": "https://www.google.com/chrome/",
        },
        {
            "name": "Adobe Acrobat Reader",
            "desc": "",
            "url": "https://get.adobe.com/reader/",
        },
    ],
    "Tools": [
        {
            "name": "j5create 360 All Around Webcam",
            "desc": "Install for Manager's Webcam firmware and Webcam Companion app.",
            "url": "https://en.j5create.com/pages/drivers#jvcu360-show",
        },
        {
            "name": "j5create 360 AI-Powered Webcam with Speakerphone",
            "desc": "Install for Meetings Webcam firmware and Webcam Companion app.",
            "url": "https://en.j5create.com/pages/drivers#jvu368-show",
        },
    ],
}

# --------------------------------------------------------------------------
# Display — nothing below this line needs editing to add a new link
# --------------------------------------------------------------------------

st.title("⬇️ Staff Downloads")
st.caption(
    "Straight-to-source links for setting up or reinstalling software on a CLC-LBU device. "
    "Got a new device? Start with **New device setup** below."
)
st.info(
    "If you're not sure whether you have permission to install something, or a link looks "
    "out of date, check with the office before proceeding.",
    icon="ℹ️",
)

st.divider()

for category, items in DOWNLOADS.items():
    st.subheader(category)
    cols = st.columns(2)
    for i, item in enumerate(items):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{item['name']}**")
                if item["desc"]:
                    st.caption(item["desc"])
                st.link_button("Go to download →", item["url"], use_container_width=True)
    st.write("")

st.divider()
st.caption(
    "Maintained by editing the `DOWNLOADS` dictionary at the top of `49_Staff_Downloads.py` "
    "directly in GitHub — no redeploy steps or database changes required."
)
