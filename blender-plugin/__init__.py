import bpy
from importlib import import_module as im
from pathlib import Path
from mathutils import Vector

bl_info = {
  "name": "Sollumz Extensions",
  "author": "Duke of Sussex",
  "description": "This plugin provides additional tools for the Sollumz plugin.",
  "blender": (3, 4, 1),
  "version": (1, 0, 0),
  "location": "",
  "warning": "",
  "category": "Import-Export"
}

SOLLUMZ_PACKAGE = "bl_ext.repo_sollumz_org.sollumz"

SOLLUMZ_PT_YMAP_TOOL_PANEL = im(f'{SOLLUMZ_PACKAGE}.ymap.ui').SOLLUMZ_PT_YMAP_TOOL_PANEL
SOLLUMZ_OT_base = im(f'{SOLLUMZ_PACKAGE}.sollumz_helper').SOLLUMZ_OT_base
EntityLodLevel = im(f'{SOLLUMZ_PACKAGE}.sollumz_properties').EntityLodLevel
EntityPriorityLevel = im(f'{SOLLUMZ_PACKAGE}.sollumz_properties').EntityPriorityLevel
SollumType = im(f'{SOLLUMZ_PACKAGE}.sollumz_properties').SollumType

def set_entity_definitions(flags):
  for obj in bpy.context.selected_objects:
    if obj.sollum_type != SollumType.DRAWABLE:
      print(f"Skipping {obj.name}...")
      continue

      obj.entity_properties.flags = flags + (1 << 19) + (1 << 20)
      if obj.rotation_euler.x != 0 or obj.rotation_euler.y != 0:
        obj.entity_properties.flags += 1

      obj.entity_properties.guid = 0
      obj.entity_properties.parent_index = -1
      obj.entity_properties.lod_dist = 200
      obj.entity_properties.child_lod_dist = 0
      obj.entity_properties.lod_level = EntityLodLevel.LODTYPES_DEPTH_ORPHANHD
      obj.entity_properties.num_children = 0
      obj.entity_properties.priority_level = EntityPriorityLevel.PRI_REQUIRED
      obj.entity_properties.ambient_occlusion_multiplier = 255
      obj.entity_properties.artificial_ambient_occlusion = 255
      obj.entity_properties.tint_value = 0

class SOLLUMZ_EX_TOOL_PT_PANEL(bpy.types.Panel):
  bl_label = "Duke's Extensions"
  bl_idname = "SOLLUMZ_EX_TOOL_PT_PANEL"
  bl_category = "Sollumz Tools"
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_options = {"DEFAULT_CLOSED"}

  def draw_header(self, context):
    self.layout.label(text="", icon="PROPERTIES")

  def draw(self, context):
    layout = self.layout
    row = layout.column()
    row.operator("sollumz_ex.import_missing_props")
    row.operator("sollumz_ex.move_to_parent")

class SOLLUMZ_EX_TOOL_IMPORT_MISSING_PROPS(SOLLUMZ_OT_base, bpy.types.Operator):
  """Import missing props for a Sollumz YMAP object"""
  bl_idname = "sollumz_ex.import_missing_props"
  bl_label = f"Import Missing Props"

  @classmethod
  def poll(cls, context):
    return any("not found" in obj.name for obj in bpy.context.scene.objects if obj.visible_get())

  def run(self, context):
    missing_objects = [obj for obj in bpy.context.scene.objects if "not found" in obj.name and obj.visible_get()]
    missing_props = [{"name": name} for name in set([obj.name.split(" (")[0] for obj in missing_objects])]
    asset_library = bpy.context.preferences.filepaths.asset_libraries.get("GTA FiveM")
    files = [fp for fp in Path(asset_library.path).glob("**/*.blend") if fp.is_file()]

    for i, obj in enumerate(missing_objects):
      name = obj.name.split(" (")[0]
      prop = bpy.context.scene.objects.get(name, None)

      if prop is None:
        for file in [f for f in files if f.name.startswith(name[0]) or f.name.startswith('_assets')]:
          print(f"Checking '{file.name}'...")
          bpy.ops.wm.append(directory=str(file)+"/Object/", do_reuse_local_id=True, clear_asset_data=True, files=missing_props)

          # Read asset files once
          files.remove(file)

          prop = bpy.context.scene.objects.get(name, None)
          if prop is not None:
            break

      if prop is None:
        self.error(f"{obj.name} not found in asset library!")
        continue

      if prop.sollum_type == SollumType.DRAWABLE_GEOMETRY:
        prop.sollum_type = SollumType.DRAWABLE

      copy = prop

      if prop.location != Vector([0, 0, 0]):
        copy = prop.copy()
        bpy.context.scene.collection.objects.link(copy)

      if copy.users_collection[-1].name != obj.users_collection[-1].name:
        copy.users_collection[-1].objects.unlink(copy)
        obj.users_collection[-1].objects.link(copy)

      copy.entity_properties.archetype_name = obj.entity_properties.archetype_name
      copy.entity_properties.flags = obj.entity_properties.flags
      copy.entity_properties.guid = obj.entity_properties.guid
      copy.entity_properties.parent_index = obj.entity_properties.parent_index
      copy.entity_properties.lod_dist = obj.entity_properties.lod_dist
      copy.entity_properties.child_lod_dist = obj.entity_properties.child_lod_dist
      copy.entity_properties.lod_level = obj.entity_properties.lod_level
      copy.entity_properties.num_children = obj.entity_properties.num_children
      copy.entity_properties.priority_level = obj.entity_properties.priority_level
      copy.entity_properties.ambient_occlusion_multiplier = obj.entity_properties.ambient_occlusion_multiplier
      copy.entity_properties.artificial_ambient_occlusion = obj.entity_properties.artificial_ambient_occlusion
      copy.entity_properties.tint_value = obj.entity_properties.tint_value
      copy.matrix_world = obj.matrix_world
      copy.location = obj.location
      copy.scale = obj.scale
      copy.parent = obj.parent
      bpy.data.objects.remove(obj)

    bpy.data.batch_remove(ids=bpy.data.libraries)
    self.message(f"Successfully imported all missing props!")

class SOLLUMZ_EX_TOOL_MOVE_TO_PARENT(SOLLUMZ_OT_base, bpy.types.Operator):
  """Move child objects to parents"""
  bl_idname = "sollumz_ex.move_to_parent"
  bl_label = f"Move To Parents"

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects)

  def run(self, context):
    for obj in context.selected_objects:
      if not obj.parent:
        self.error(f"{obj.name} has no parent!")
        continue

      obj.users_collection[-1].objects.unlink(obj)
      obj.parent.users_collection[-1].objects.link(obj)

    self.message(f"Successfully moved child objects to parents!")

class SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_DYNAMIC(bpy.types.Operator):
  bl_idname = "sollumz_ex.set_entity_definitions_dynamic"
  bl_label = "Dynamic"
  bl_description = "Set selected entities as dynamic"

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects)

  def execute(self, context):
    set_entity_definitions(0)

    return {'FINISHED'}

class SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_STATIC(bpy.types.Operator):
  bl_idname = "sollumz_ex.set_entity_definitions_static"
  bl_label = "Static"
  bl_description = "Set selected entities as static"

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects)

  def execute(self, context):
    set_entity_definitions(32)

    return {'FINISHED'}

class SOLLUMZ_EX_TOOL_PT_FLAGS_PANEL(SOLLUMZ_OT_base, bpy.types.Panel):
  bl_label = "Set YMAP Entity Definitions"
  bl_idname = "SOLLUMZ_EX_TOOL_PT_FLAGS_PANEL"
  bl_category = "Sollumz Tools"
  bl_parent_id = "SOLLUMZ_EX_TOOL_PT_PANEL"
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_options = {"HEADER_LAYOUT_EXPAND"}

  def draw_header(self, context):
    pass

  def draw(self, context):
    layout = self.layout
    grid = layout.grid_flow(align=True, row_major=True)
    grid.scale_x = 0.7
    grid.operator(SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_DYNAMIC.bl_idname)
    grid.operator(SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_STATIC.bl_idname)

def register():
  bpy.utils.register_class(SOLLUMZ_EX_TOOL_PT_PANEL)
  bpy.utils.register_class(SOLLUMZ_EX_TOOL_IMPORT_MISSING_PROPS)
  bpy.utils.register_class(SOLLUMZ_EX_TOOL_MOVE_TO_PARENT)
  bpy.utils.register_class(SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_DYNAMIC)
  bpy.utils.register_class(SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_STATIC)
  bpy.utils.register_class(SOLLUMZ_EX_TOOL_PT_FLAGS_PANEL)


def unregister():
  bpy.utils.unregister_class(SOLLUMZ_EX_TOOL_PT_PANEL)
  bpy.utils.unregister_class(SOLLUMZ_EX_TOOL_IMPORT_MISSING_PROPS)
  bpy.utils.unregister_class(SOLLUMZ_EX_TOOL_MOVE_TO_PARENT)
  bpy.utils.unregister_class(SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_DYNAMIC)
  bpy.utils.unregister_class(SOLLUMZ_EX_TOOL_SET_ENTITY_DEFINITIONS_STATIC)
  bpy.utils.unregister_class(SOLLUMZ_EX_TOOL_PT_FLAGS_PANEL)

if __name__ == "__main__":
  register()
