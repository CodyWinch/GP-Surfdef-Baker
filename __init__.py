# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.props import *
from bpy.types import PropertyGroup, Panel, Operator

bl_info = {
    "name": "GP SurfDef Baker",
    "author": "Cody Winchester",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic"
}


class GPBScnProperties(PropertyGroup):
    target_object: StringProperty(
        default='', description="Target mesh to deform the active grease pencil object")

    # copy_and_separate_bool: BoolProperty(default=False, description="")

    # copy_scale: FloatProperty(default=1.00, min=0.00,
    #                           max=100.00, description="Scale of deformation")

    # mirror_axis: IntProperty(default=0, min=0, max=2,
    #                          description="Axis to mirror shape keys")


def main(context):
    data = bpy.data
    scn = context.scene
    scn_props = context.scene.gpb_props

    tar = data.objects[scn_props.target_object]
    gp = context.active_object

    # Cache active frame strokes world space data
    v_cos = []
    e_inds = []
    ind_offset = 0
    ref_frame = gp.data.layers.active.active_frame
    for stro in ref_frame.strokes:
        strokes = []

        for p, po in enumerate(stro.points):
            strokes.append(gp.matrix_world @ po.co)
            v_cos.append(gp.matrix_world @ po.co)

            if p > 0:
                e_inds.append([p-1+ind_offset, p+ind_offset])

        ind_offset += len(stro.points)

    # Create temp mesh from gp
    mesh_name = 'GP Temp Bake Mesh'
    mesh_dat = data.meshes.new(mesh_name)

    mesh_dat.from_pydata(v_cos, e_inds, [])
    mesh_dat.update()
    bake_ob = data.objects.new(mesh_name, mesh_dat)

    mod = bake_ob.modifiers.new('Surface Deform', 'SURFACE_DEFORM')
    mod.target = tar

    # Bind mesh object to target object
    context.collection.objects.link(bake_ob)
    bake_ob.select_set(True)
    context.view_layer.objects.active = bake_ob

    bpy.ops.object.surfacedeform_bind(modifier=mod.name)

    scn.frame_set(scn.frame_start)

    cur_frames = [f.frame_number for f in gp.data.layers.active.frames]
    for i in range(scn.frame_end-scn.frame_start+1):
        deps_g = context.evaluated_depsgraph_get()
        bake_eval = bake_ob.evaluated_get(deps_g)
        mesh = bake_eval.to_mesh()

        if scn.frame_current not in cur_frames:
            frame = gp.data.layers.active.frames.new(scn.frame_current)
            for ref_stroke in ref_frame.strokes:
                stroke = frame.strokes.new()
                stroke.line_width = ref_stroke.line_width
                stroke.display_mode = ref_stroke.display_mode
                for ref_po in ref_stroke.points:
                    stroke.points.add(
                        1, pressure=ref_po.pressure, strength=ref_po.strength)
                    stroke.points[-1].co = ref_po.co
        else:
            frame = [
                f for f in gp.data.layers.active.frames if f.frame_number == scn.frame_current][0]

        ind = 0
        for stro in frame.strokes:
            for po in stro.points:
                po.co = bake_ob.matrix_world @ mesh.vertices[ind].co
                ind += 1

        scn.frame_set(scn.frame_current+1)

    data.meshes.remove(mesh_dat)
    # data.objects.remove(bake_ob)

    # Reset active selection
    gp.select_set(True)
    context.view_layer.objects.active = gp

    return


class BakeGPSurfaceDeform(Operator):
    """Bind and bake the surface deform of the active Grease Pencil object"""
    bl_idname = "object.bake_gp_surfdef"
    bl_label = "Bake GP Surface Deform"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'GPENCIL'

    @classmethod
    def poll(cls, context):
        return context.scene.gpb_props.target_object is not ''

    @classmethod
    def poll(cls, context):
        return context.scene.gpb_props.target_object in bpy.data.objects

    def execute(self, context):
        main(context)
        return {'FINISHED'}


class GPB_PT_tools_panel(Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GP SurfDef Bake'

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None and obj.type == 'GPENCIL':
            return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        data = bpy.data
        aobj = context.active_object

        scn_prop = scn.gpb_props

        box = layout.box()

        row = box.row()
        row.alignment = 'CENTER'
        row.label(text="Target Mesh")

        row = box.row(align=True)
        row.alignment = 'CENTER'
        row.prop_search(scn_prop, 'target_object', data,
                        'objects', text='')
        row.alignment = 'CENTER'

        row = box.row(align=True)
        row.alignment = 'CENTER'
        row.operator("object.bake_gp_surfdef",
                     text='Bake Surface Deform')
        row.scale_y = 1.5
        row.alignment = 'CENTER'


def register():
    bpy.utils.register_class(BakeGPSurfaceDeform)
    bpy.utils.register_class(GPBScnProperties)
    bpy.utils.register_class(GPB_PT_tools_panel)
    bpy.types.Scene.gpb_props = PointerProperty(type=GPBScnProperties)
    return


def unregister():
    bpy.utils.unregister_class(BakeGPSurfaceDeform)
    bpy.utils.unregister_class(GPBScnProperties)
    bpy.utils.unregister_class(GPB_PT_tools_panel)
    del bpy.types.Scene.gpb_props
    return


if __name__ == "__main__":
    register()
