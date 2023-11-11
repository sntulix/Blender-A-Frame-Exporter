bl_info = {
    "name": "Blender A-Frame Exporter",
    "blender": (3, 6, 1),
    "category": "Export",
    "description": "Export Blender scene to an A-Frame compatible HTML.",
    "author": "Takahiro Shizuki",
    "version": (0, 1, 0),
}

import bpy, math
import os
from bpy.props import StringProperty, PointerProperty
from bpy_extras.io_utils import ExportHelper

# The operator that handles the export
class EXPORT_OT_aframe(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.a_frame"
    bl_label = "Export A-Frame"
    filename_ext = ""

    exclude_keywords: StringProperty(
        name="Exclude Keywords",
        description="Keywords to exclude objects from the export",
        default="exclude1 exclude2 exclude3 ..."
    )
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)

        # デフォルトのファイルパスを設定
        self.filepath = context.scene.aframe_exporter_props.output_path + context.scene.aframe_exporter_props.output_folder
        return {'RUNNING_MODAL'}

    def execute(self, context):
        # 出力ディレクトリのパスを設定
        if not os.path.exists(self.filepath):
            os.mkdir(self.filepath)
            
        output_directory = bpy.path.abspath(self.filepath)

        # 既存の選択をクリア
        bpy.ops.object.select_all(action='DESELECT')
        
        # エクスポート対象のオブジェクトを取得
        objects_to_export = [
            obj for obj in bpy.context.scene.objects 
            if obj.type == 'MESH' and not any(keyword in obj.name for keyword in self.exclude_keywords.split())
        ]
        
        # シーン内の最初のカメラを取得
        camera_data = next((cam for cam in bpy.context.scene.objects if cam.type == 'CAMERA'), None)
        
        # オブジェクトを.objとしてエクスポート
        for obj in objects_to_export:
            obj.select_set(True)
            context.view_layer.objects.active = obj
            bpy.ops.export_scene.obj(filepath=os.path.join(output_directory, f"{obj.name}.obj"), use_selection=True, use_materials=True, use_triangles=True, path_mode='COPY')
            obj.select_set(False)
        
        # A-FrameのHTMLコンテンツを作成
        html_content = create_aframe_html(
            context.scene.aframe_exporter_props.title,
            context.scene.aframe_exporter_props.sky,
            objects_to_export,
            camera_data,
            output_directory)
        
        # HTMLファイルに書き出し
        with open(os.path.join(output_directory, "index.html"), 'w') as f:
            f.write(html_content)
        
        return {'FINISHED'}

def create_aframe_html(title, sky, objects, camera_data, output_directory):
    # <a-assets> タグ内のアイテムを定義
    assets_html = '        <a-assets>\n'
    if sky!='':
        assets_html += f'            <img id="sky" src="sky.jpg">\n'
    for obj in objects:
        obj_file = f"{obj.name}.obj"
        mtl_file = f"{obj.name}.mtl"
        assets_html += f'            <a-asset-item id="{obj.name}-obj" src="{obj_file}"></a-asset-item>'
        assets_html += f'<a-asset-item id="{obj.name}-mtl" src="{mtl_file}"></a-asset-item>\n'


    assets_html += '        </a-assets>\n'


    entities_html = ''
    if sky!='':
        entities_html += f'        <a-sky src="#sky"></a-sky>\n'

    for obj in objects:
        # BlenderからA-Frameへの位置の変換
        position = f"{obj.location.x} {obj.location.z} {obj.location.y*-1}"

        # Blenderのオイラー角を度に変換
        rotation = obj.rotation_euler
        rotation_deg = [math.degrees(angle) for angle in rotation]

        # A-Frameの座標系に合わせて軸を変換
        aframe_rotation = f"{rotation_deg[0]} {rotation_deg[2]} {rotation_deg[1]}"

        scale = f"{obj.scale.x} {obj.scale.z} {obj.scale.y}"
        entities_html += f'        <a-entity id="{obj.name}" obj-model="obj: #{obj.name}-obj; mtl: #{obj.name}-mtl" position="{position}" rotation="{aframe_rotation}" scale="{scale}" shadow></a-entity>\n'


    camera_html = ''
    if camera_data:
        # BlenderからA-Frameへの位置の変換
        camera_position = f"{camera_data.location.x} {camera_data.location.z} {camera_data.location.y*-1}"

        # Blenderのオイラー角を度に変換
        # camera_data.rotation is expected to be a list of Euler angles in radians
        camera_rotation = camera_data.rotation_euler
        camera_rotation_deg = [int(math.degrees(angle)) for angle in camera_rotation]

        # A-Frameの座標系に合わせて軸を変換
        # Since camera_rotation_deg is a list, we access its elements by index
        aframe_camera_rotation = f"{camera_rotation_deg[0]} {camera_rotation_deg[2]} {camera_rotation_deg[1]}"

        camera = bpy.data.cameras[camera_data.name]
        fov = math.degrees(camera.angle)
        camera_html = f'<a-camera position="{camera_position}" rotation="{aframe_camera_rotation}" fov="{fov}"></a-camera>\n'

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://aframe.io/releases/1.2.0/aframe.min.js"></script>
</head>
<body>
    <a-scene>
        {camera_html}
{assets_html}
{entities_html}
    </a-scene>
</body>
</html>"""

    return html_content

# UI Panel
class EXPORT_PT_aframe(bpy.types.Panel):
    bl_label = "A-Frame Exporter"
    bl_idname = "EXPORT_PT_aframe"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'A-Frame'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        aframe_props = scene.aframe_exporter_props

        layout.prop(aframe_props, "title")
        layout.prop(aframe_props, "sky")
        layout.prop(aframe_props, "output_folder")
        layout.prop(aframe_props, "output_path")
        layout.prop(aframe_props, "exclude_keywords")
        
        layout.operator("export_scene.a_frame", text="Export A-Frame HTML")

# Property group to hold properties for the exporter
class AFrameExporterProperties(bpy.types.PropertyGroup):
    title: StringProperty(
        name="Title Name",
        description="HTML Title exported",
        default="Walk Through VR",
        maxlen=1024,
    )
    sky: StringProperty(
        name="Sky File",
        description="sky texture",
        default="sky.jpg",
        maxlen=1024,
    )
    output_folder: StringProperty(
        name="Folder Name",
        description="Name of the folder where the exported files will be saved",
        default="aframe_export",
        maxlen=1024,
    )
    output_path: StringProperty(
        name="Folder Path",
        description="Path to the folder where the exported files will be saved",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    exclude_keywords: StringProperty(
        name="Exclude Keywords",
        description="Keywords to exclude objects from the export",
        default="exclude1 exclude2 exclude3 ..."
    )

# Registration
def register():
    bpy.utils.register_class(EXPORT_OT_aframe)
    bpy.utils.register_class(EXPORT_PT_aframe)
    bpy.utils.register_class(AFrameExporterProperties)
    bpy.types.Scene.aframe_exporter_props = PointerProperty(type=AFrameExporterProperties)

def unregister():
    bpy.utils.unregister_class(EXPORT_OT_aframe)
    bpy.utils.unregister_class(EXPORT_PT_aframe)
    bpy.utils.unregister_class(AFrameExporterProperties)
    del bpy.types.Scene.aframe_exporter_props

if __name__ == "__main__":
    register()
