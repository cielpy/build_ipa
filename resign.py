#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 ciel <ciel@cieldeMBP>
#
# Distributed under terms of the MIT license.

"""
resign ipa
"""
import shutil
import os
import zipfile
import re
from call_cmd import call

def resign(ipa=None, build_info=None):
    if os.path.exists('Payload'):
        shutil.rmtree('Payload')
    resign_info = build_info['resign']
    tmp_dir = call('mktemp -d')[1]
    call('unzip -q {} -d {}'.format(ipa, tmp_dir))
    extentions_info = None
    if 'extentions' in resign_info:
        extentions_info = resign_info['extentions']
    if extentions_info:
        for extention in extentions_info:
            resign_app('{}/Payload/{}.app/PlugIns/{}.appex'.format(tmp_dir, build_info['scheme'], extention['scheme']), resign_info['certificate'], extention['provisioning_profile'], None, extention['bundle_id'])
    
    resign_app('{}/Payload/{}.app'.format(tmp_dir, build_info['scheme']), resign_info['certificate'], resign_info['provisioning_profile'], resign_info['app_name'], resign_info['bundle_id'])
    file_name_pieces = ipa.split('/')[-1].split('.ipa')
    resign_ipa_name = file_name_pieces[0] + '-resign.ipa'
    resign_ipa = ipa.replace(ipa.split('/')[-1], resign_ipa_name)
    zipDir(tmp_dir, resign_ipa)
    shutil.rmtree(tmp_dir)
    os.remove(ipa)
    return (0, resign_ipa)

def resign_app(app=None, cert=None, profile=None, app_name=None, bundle_id=None):
    signature = app + '/_CodeSignature'
    if os.path.exists(signature):
        shutil.rmtree(signature)
    shutil.copyfile(profile, app + '/embedded.mobileprovision')
    tmp_entitlements = '/tmp/entitlements.plist'
    with open(tmp_entitlements, 'w+') as f:
        call('codesign -d --entitlements - ' + app, f)

    with open(tmp_entitlements, 'r+', encoding='ISO-8859-1') as f:
        lines = f.read().split('\n')
        to_delete = lines[0]
        f.seek(0)
        for line in lines:
            if line != to_delete:
                if line == lines[1]:
                    words = line.split('xml')
                    line = line.replace(words[0], '<?')
                f.write(line + '\n')
        f.truncate()
    
    team_id = read_profile_attribute(profile, 'com.apple.developer.team-identifier')

    if bundle_id:
        call("/usr/libexec/PlistBuddy -c \"Set :application-identifier {}\" {}".format('{}.{}'.format(team_id, bundle_id), tmp_entitlements))
        call("/usr/libexec/PlistBuddy -c \"Set :com.apple.developer.team-identifier {}\" {}".format(team_id, tmp_entitlements))
        call("/usr/libexec/PlistBuddy -c \"Set :CFBundleIdentifier {}\" {}/Info.plist".format(bundle_id, app))
    else:
        entitlements_bundle_id = read_profile_attribute(profile, 'application-identifier')
        pure_bundle_id = entitlements_bundle_id.replace('{}.'.format(team_id), '')

        call("/usr/libexec/PlistBuddy -c \"Set :application-identifier {}\" {}".format(entitlements_bundle_id, tmp_entitlements))
        call("/usr/libexec/PlistBuddy -c \"Set :com.apple.developer.team-identifier {}\" {}".format(team_id, tmp_entitlements))
        call("/usr/libexec/PlistBuddy -c \"Set :CFBundleIdentifier {}\" {}/Info.plist".format(pure_bundle_id, app))

    if app_name:
        call("/usr/libexec/PlistBuddy -c \"Set :CFBundleName {}\" {}/Info.plist".format(app_name, app))


    aps_env = read_profile_attribute(profile, 'aps-environment')
    if aps_env:
        call("/usr/libexec/PlistBuddy -c \"Set :aps-environment {}\" {}".format(aps_env, tmp_entitlements))

    call('codesign -f -s \"{}\" \'--entitlements\' \'{}\' {}'.format(cert, tmp_entitlements, app))
    os.remove(tmp_entitlements)
    
def read_profile_attribute(profile=None, attribute=None):
    if not profile:
        return None
    if not attribute:
        return None

    key_value_res = call('egrep -a -A 1 ' + attribute + ' ' + profile)
    if key_value_res[0] != 0:
        return None
    all_keys = re.findall(".*</(.*)>.*", key_value_res[1])

    value = re.findall(".*<{}>(.*)</{}>.*".format(all_keys[1], all_keys[1]), key_value_res[1])
    if value:
        return value[0]
    else:
        return None

def zipDir(dirPath, zipPath):
    zipf = zipfile.ZipFile(zipPath, mode='w', compression=zipfile.ZIP_DEFLATED)
    lenDirPath = len(dirPath)
    for root, _ , files in os.walk(dirPath):
        for file in files:
            filePath = os.path.join(root, file)
            zipf.write(filePath ,filePath[lenDirPath :])
    zipf.close()