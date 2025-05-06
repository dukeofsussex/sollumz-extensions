import bpy
from contextlib import redirect_stdout as rstdout, redirect_stderr as rstderr
from importlib import import_module as im
from io import StringIO
import re
from pathlib import Path
import sys

dir = str(Path(bpy.data.filepath))
if not dir in sys.path:
  sys.path.append(dir)

from config import *
from utils import *

drawable = im(f'{SOLLUMZ_PACKAGE}.cwxml.drawable')
fragment = im(f'{SOLLUMZ_PACKAGE}.cwxml.fragment')
ydrimport = im(f'{SOLLUMZ_PACKAGE}.ydr.ydrimport')
yftimport = im(f'{SOLLUMZ_PACKAGE}.yft.yftimport')

ALL_ASSET_GROUPS = list(ASSET_GROUPS.keys()) + list({f'{VEHICLE_GROUP}/{veh[0]}' for veh in VEHICLES}) + [ UNGROUPED ]
ASSET_GROUP_REGEXES = { group: re.compile(ASSET_GROUPS[group]) for group in ASSET_GROUPS }
BLENDER_STDOUT = StringIO()
DUPLICATE_REGEX = re.compile("\.\d+$")
GROUPED_ASSETS = { group: { 'assets': [], 'total': 0 } for group in ALL_ASSET_GROUPS }
LINE_CLEAR = '\033[2K\033[1G'
SUPPORTED_ASSET_EXTS = [
  drawable.YDR.file_extension,
  fragment.YFT.file_extension
]
TEXTURE_EXT = ".dds"
TEXTURE_PLACEHOLDER = 'givemechecker'

def cleanDataGroup(status, dataGroup):
  for item in dataGroup:
    if item.users == 0:
      print(f'{status} >>> Deleted {colourise(item.name, Colour.RED)}')
      dataGroup.remove(item)

def getOriginalAsset(name, dataSet):
  return dataSet.get(name) or (getOriginalAsset('_'.join(name.split('_')[1:]), dataSet) if '_' in name else None)

def hasHiResVeh(name):
  hiRes = f'{name}_hi'

  return (not name.endswith('_hi')
    and ((getOriginalAsset(hiRes, bpy.data.objects) is not None)
      or any(a['name'] == hiRes for ga in GROUPED_ASSETS for a in GROUPED_ASSETS[ga]['assets'])))

def revertFailedImport():
  failedImports = [obj for obj in bpy.data.objects if not obj.asset_data]

  for obj in failedImports:
    bpy.data.objects.remove(obj)

def save(status, filepath):
  try:
    print(f'{status} >>> {colourise("Saving", Colour.PURPLE)}')
    with rstdout(BLENDER_STDOUT), rstderr(BLENDER_STDOUT):
      bpy.ops.wm.save_as_mainfile(filepath=filepath)
  except:
    # Ignore packing error
    pass
  finally:
    Path(filepath + '1').unlink(missing_ok=True)

def importAssets():
  print(f'Importing assets from {colourise(IMPORT_DIRECTORY, Colour.CYAN)}')
  assetPad = 0
  missingTextures = {
    TEXTURE_PLACEHOLDER: None
  }
  settings = ImportSettings()
  textures = []
  op = YTFHelperOperator(settings)

  for file in (p for p in Path(IMPORT_DIRECTORY).rglob("*") if p.is_file()):
    ext = "".join(file.suffixes)
    name = file.name[0:-len(ext)]
    path = str(file.parents[0].absolute())

    print(f'Processing {file.name}...', end=LINE_CLEAR)

    if ext == TEXTURE_EXT:
      textures.append({
        'name': name,
        'parent': file.parents[0].name,
        'path': path
      })
    elif ext in SUPPORTED_ASSET_EXTS:
      assetGroup = file.name[0:file.name.find("_")]
      key = UNGROUPED
      veh = None

      for [k, v] in ASSET_GROUP_REGEXES.items():
          if v.search(name):
            key = k

      if key == UNGROUPED:
        veh = next((veh for veh in VEHICLES if name.startswith(veh)), None)

        if veh is not None:
          key = f'{VEHICLE_GROUP}/{veh[0]}'

      GROUPED_ASSETS[key]['assets'].append({
        'name': name,
        'path': path,
        'ext': ext,
        'isVeh': veh is not None,
      })
      GROUPED_ASSETS[key]['total'] += 1

      if len(file.name) > assetPad:
        assetPad = len(file.name)

  groupCounter = 0
  populatedGroups = [group for group in ALL_ASSET_GROUPS if GROUPED_ASSETS[group]['total'] > 0]
  totalGroups = len(populatedGroups)

  for group in populatedGroups:
    assetCounter = 0
    assetCounterPad = len(str(GROUPED_ASSETS[group]['total']))
    blendFile = f"{group}.blend"
    blendFilePath = str(Path(ASSET_LIBRARY_DIRECTORY, blendFile).absolute())
    changes = 0
    foundImages = []
    groupCounter += 1
    groupStatus = f"[{groupCounter:{len(str(totalGroups))}}/{totalGroups}]"

    print(f"{groupStatus}: Group {colourise(group, Colour.CYAN)}")

    if Path(blendFilePath).is_file():
      print(f'> Opening {colourise(blendFile, Colour.GREEN)}', end=' ')
      with rstdout(BLENDER_STDOUT), rstderr(BLENDER_STDOUT):
        bpy.ops.wm.open_mainfile(filepath=blendFilePath, check_existing=True)
    else:
      print(f'> Creating {colourise(blendFile, Colour.YELLOW)}', end=' ')
      with rstdout(BLENDER_STDOUT), rstderr(BLENDER_STDOUT):
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.file.autopack_toggle()
        save(groupStatus, blendFilePath)

    print(f'> Importing {colourise(GROUPED_ASSETS[group]["total"], Colour.CYAN)} files')

    for asset in GROUPED_ASSETS[group]['assets']:
      assetCounter += 1
      assetStatus = f'{groupStatus}[{assetCounter:{assetCounterPad}}/{GROUPED_ASSETS[group]["total"]}]: {colourise((asset["name"] + asset["ext"]).ljust(assetPad), Colour.CYAN)}'

      print(assetStatus, end=' ')

      if asset['isVeh'] and hasHiResVeh(asset['name']):
        print(f'> Skipping {colourise("low res", Colour.PURPLE)}')
        continue

      importedObj = getOriginalAsset(asset['name'], bpy.data.objects)

      if importedObj is not None:
        print(f'> Asset {colourise("found", Colour.PURPLE)}')
      else:
        print(f'> Importing {colourise(asset["ext"][1:-4].upper(), Colour.CYAN)}')

        try:
          with rstdout(BLENDER_STDOUT), rstderr(BLENDER_STDOUT):
            path = str(Path(asset["path"], asset['name'] + asset['ext']).absolute())
            if asset['ext'] == drawable.YDR.file_extension:
              ydrimport.import_ydr(path, settings)
            elif asset['ext'] == fragment.YFT.file_extension:
              yftimport.import_yft(path, op)
            else:
              raise Exception(f'Unsupported asset type: {asset["ext"]}')
          changes += 1
        except Exception as e:
          print(f'{assetStatus} > {colourise(f"Failed: {e}", Colour.RED)}')
          revertFailedImport()
          continue

        importedObj = getOriginalAsset(asset['name'], bpy.data.objects)

        if importedObj is None:
          print(f'{assetStatus} > {colourise("Failed: Not Found", Colour.RED)}')
          revertFailedImport()
          continue
        elif importedObj.name != asset['name']:
          print(f'{assetStatus} > Fixed {colourise("asset name", Colour.GREEN)}')
          importedObj.name = asset['name']

      genPreview = False
      lastTexturePath = None

      for slot in importedObj.material_slots.values():
        for node in slot.material.node_tree.nodes:
          if (node.type != 'TEX_IMAGE' or not node.image):
            continue

          optimalName = node.image.name.lower().split('.')[0]

          if node.image.name != optimalName:
            og = bpy.data.images.get(optimalName)

            if og is not None:
              print(f'{assetStatus} > Replaced {colourise(node.image.name, Colour.YELLOW)} > {colourise(og.name, Colour.GREEN)}')
              genPreview = True
              node.image = og
              continue

          node.image.name = optimalName

          if node.image.name in foundImages:
            genPreview = True
            continue

          if (node.image.packed_file or node.image.has_data or node.image.name in missingTextures):
            continue

          texture = next((t for t in textures if t['parent'].lower() == asset['name'].lower() and t['name'].lower() == node.image.name), None)

          if texture is None:
            texture = next((t for t in textures if t['name'].lower() == node.image.name), None)

          if texture is None:
            missingTextures[node.image.name] = asset['name']
            continue

          print(f'{assetStatus} > Added {colourise(node.image.name, Colour.GREEN)}')
          changes += 1
          foundImages.append(node.image.name)

          if texture['path'] != lastTexturePath:
            with rstdout(BLENDER_STDOUT), rstderr(BLENDER_STDOUT):
              bpy.ops.file.find_missing_files(directory=texture['path'], filter_image=True)
            genPreview = True
            lastTexturePath = texture['path']

      if genPreview:
        importedObj.asset_generate_preview()

      print(f'{assetStatus} > Asset {colourise("ready", Colour.GREEN)}')

      if changes >= 25:
        save(groupStatus, blendFilePath)
        changes = 0

    print(f'{groupStatus} >>> {colourise("Cleaning up", Colour.CYAN)}')
    for obj in bpy.data.objects:
      if (not obj.asset_data
          or re.search(DUPLICATE_REGEX, obj.name)
          or (group in ASSET_GROUPS
            and not re.search(ASSET_GROUP_REGEXES[group], obj.name)
            and any(a['name'].startswith(obj.name) for ga in GROUPED_ASSETS if ga != group for a in GROUPED_ASSETS[ga]['assets']))
          or (group not in ASSET_GROUPS
            and not any(a for a in GROUPED_ASSETS[group]['assets'] if a['name'].startswith(obj.name))
            and any(a['name'].startswith(obj.name) for ga in GROUPED_ASSETS for a in GROUPED_ASSETS[ga]['assets']))
          or (obj.name in VEHICLES and hasHiResVeh(obj.name))):
        objName = colourise(obj.name.ljust(assetPad), Colour.CYAN)
        print(f'{groupStatus}: {objName}: {colourise("Deleted", Colour.RED)}')
        bpy.data.objects.remove(obj)

    cleanDataGroup(groupStatus, bpy.data.meshes)
    cleanDataGroup(groupStatus, bpy.data.materials)
    cleanDataGroup(groupStatus, bpy.data.textures)
    cleanDataGroup(groupStatus, bpy.data.images)

    save(groupStatus, blendFilePath)

  for [k, v] in missingTextures.items():
    if (k != TEXTURE_PLACEHOLDER):
      print(f'{groupStatus}: {colourise(v.ljust(assetPad), Colour.CYAN)}: Missing {colourise(k + TEXTURE_EXT, Colour.YELLOW)}')

if __name__ == "__main__":
    importAssets()
