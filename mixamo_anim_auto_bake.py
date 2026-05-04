bl_info = {
    "name": "Mixamo Helper",
    "author": "SkyClerik",
    "version": (1, 9),
    "blender": (4, 3, 0),
    "location": "Properties Editor > Tool > Scene",
    "category": "Animation",
    "description": "Optimized import and management of FBX models"
}

import bpy # type: ignore
import os
from bpy.types import PropertyGroup, Panel, Operator # type: ignore
from bpy.props import StringProperty, CollectionProperty, PointerProperty, FloatProperty, IntProperty # type: ignore
from bpy_extras.io_utils import ImportHelper # type: ignore

# Класс для хранения импортированных объектов
class ImportedObject(PropertyGroup):
    obj: PointerProperty(type=bpy.types.Object) # type: ignore

# Класс для хранения свойств аддона
class AutoBakeProperties(PropertyGroup):
    export_folder: StringProperty(
        name="Model Directory",
        description="Path to the folder with FBX files",
        subtype='DIR_PATH'
    ) # type: ignore
    current_object_name: StringProperty(
        name="Current Object",
        description="Name of the object for operations",
        default=""
    ) # type: ignore
    imported_objects: CollectionProperty(
        type=ImportedObject,
        name="Imported Objects"
    ) # type: ignore
    arrange_offset: FloatProperty(
        name="X Offset",
        description="Offset from Armature",
        default=-2.0
    ) # type: ignore
    current_index: IntProperty(
        name="Current Index",
        default=0
    ) # type: ignore
    label_name: StringProperty(
        name="Name",
        default="None"
    ) # type: ignore
    base_armature: PointerProperty(
        name="Base Armature",
        description="Select the armature to use",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'  # Ограничить выбор только арматурами
    )  # type: ignore

# Панель интерфейса в Properties Editor
class AutoBake_PT_Panel(Panel):
    bl_idname = "AUTOBAKE_PT_Panel"
    bl_label = "Mixamo Helper"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        props = context.scene.auto_bake_props

        # Проверка на наличие свойства
        if not hasattr(context.scene, 'auto_bake_props'):
            layout.label(text="Error: auto_bake_props not initialized")
            return

        # Подсчет импортированных объектов с безопасной проверкой
        imported_count = len(props.imported_objects) if hasattr(props.imported_objects, '__len__') else 0

        # Элементы интерфейса
        row = layout.row()
        row = layout.row()
        row.prop(props, "export_folder", text="Path")
        # row.operator("wm.folder_select", text="", icon='FILE_FOLDER')

        row = layout.row()
        row.prop(props, "base_armature", text="Base Armature")

        row = layout.row()
        row.operator("wm.set_pose_position", text="Set Pose Position", icon="ARMATURE_DATA")

        row = layout.row()
        row.operator("wm.import_fbx", text="Import", icon='IMPORT')

        row = layout.row()
        row.prop(props, "arrange_offset", text="X Offset")
        row.operator("wm.arrange_objects", text="Arrange", icon='MOD_ARRAY')

        row = layout.row()
        row.label(text=f"Current Object: {props.label_name}")

        row = layout.row()
        row.operator("wm.rename_action", text="Rename Animation", icon='ACTION')
        row.operator("wm.next_model", text="Next", icon='TRIA_RIGHT')

        # Условие завершения
        row = layout.row()
        if imported_count > 0 and props.current_index >= imported_count - 1:
            row.label(text="Completed ✅", icon='CHECKMARK')

        # row.operator("wm.finish_process", text="Finish", icon='CHECKMARK')

        row = layout.row()
        row.operator("wm.delete_all_imported", text="Delete All", icon='TRASH')

# Оператор для выбора папки
class FolderSelectOperator(Operator, ImportHelper):
    bl_idname = "wm.folder_select"
    bl_label = "Select Folder"
    filter_folder = True

    def execute(self, context):
        context.scene.auto_bake_props.export_folder = self.filepath
        return {'FINISHED'}

# Базовый класс для работы с импортированными объектами
class BaseImportedOperator(Operator):
    def get_props(self, context):
        return context.scene.auto_bake_props

    def set_object_visibility(self, obj, visible):
        """Рекурсивно устанавливает видимость объекта и всех его дочерних элементов."""
        obj.hide_set(not visible)
        obj.hide_render = not visible
        for child in obj.children:
            self.set_object_visibility(child, visible)

    def show_current(self, context):
        """Показывает текущий объект и его дочерние элементы, скрывая остальные."""
        props = self.get_props(context)
        for obj_entry in props.imported_objects:
            if obj_entry.obj:
                self.set_object_visibility(obj_entry.obj, False)

        if 0 <= props.current_index < len(props.imported_objects):
            current_obj = props.imported_objects[props.current_index].obj
            if current_obj:
                self.set_object_visibility(current_obj, True)

# Оператор для импорта FBX файлов
class ImportFBXOperator(BaseImportedOperator):
    bl_idname = "wm.import_fbx"
    bl_label = "Import FBX"

    def execute(self, context):
        props = self.get_props(context)
        props.imported_objects.clear()
        props.current_index = 0
        props.label_name = "None"

        armature = bpy.data.objects.get("Armature")
        if not armature:
            self.report({'WARNING'}, "Armature object not found!")
            return {'CANCELLED'}

        # Проверка указанной директории
        if not os.path.isdir(props.export_folder):
            self.report({'WARNING'}, "Specified directory does not exist!")
            return {'CANCELLED'}

        base_pos = armature.location.copy()
        base_pos.x += props.arrange_offset

# тут вставь проверку указаной директории

        # Импорт всех FBX файлов из указанной директории
        for file in os.listdir(props.export_folder):
            if file.lower().endswith(".fbx"):
                file_path = os.path.join(props.export_folder, file)
                name = os.path.splitext(file)[0]

                try:
                    bpy.ops.import_scene.fbx(filepath=file_path)
                    obj = context.selected_objects[0]
                    obj.name = name
                    obj.location = base_pos

                    entry = props.imported_objects.add()
                    entry.obj = obj
                except Exception as e:
                    self.report({'ERROR'}, f"Import error for {file}: {str(e)}")

        if props.imported_objects:
            props.label_name = props.imported_objects[0].obj.name
            self.show_current(context)

        return {'FINISHED'}

# Оператор для принудительной установки позы
class SetPosePositionOperator(Operator):
    bl_idname = "wm.set_pose_position"
    bl_label = "Set Pose Position"

    def execute(self, context):
        props = context.scene.auto_bake_props
        # Проверка, что арматура выбрана
        armature = props.base_armature  # Получаем объект арматуры напрямую
        if armature:
            if armature.type == 'ARMATURE':
                armature.data.pose_position = 'POSE'
                self.report({'INFO'}, f"Pose position set for {armature.name}")
            else:
                self.report({'WARNING'}, "Selected object is not an armature!")
        else:
            self.report({'WARNING'}, "No armature selected!")

        return {'FINISHED'}

# Оператор для перехода к следующему объекту
class NextModelOperator(BaseImportedOperator):
    bl_idname = "wm.next_model"
    bl_label = "Next"

    def execute(self, context):
        props = self.get_props(context)
        props.current_index += 1

        if props.imported_objects:
            max_index = len(props.imported_objects) - 1
            if props.current_index > max_index:
                props.current_index = max_index
                self.set_object_visibility(props.imported_objects[props.current_index].obj, False)
                self.report({'INFO'}, "No more objects!")
            else:
                props.label_name = props.imported_objects[props.current_index].obj.name
                self.show_current(context)

        else:
            self.report({'INFO'}, "No imported objects!")

        return {'FINISHED'}

# Оператор для завершения процесса
class FinishProcessOperator(Operator):
    bl_idname = "wm.finish_process"
    bl_label = "Finish"

    @classmethod
    def poll(cls, context):
        try:
            props = context.scene.auto_bake_props
            imported_count = len(props.imported_objects)
            current_index = props.current_index
            return imported_count > 0 and current_index >= imported_count - 1
        except AttributeError:
            return False

    def execute(self, context):
        self.report({'INFO'}, "Process finished!")
        return {'FINISHED'}

# Оператор для удаления всех импортированных объектов
class DeleteAllImportedOperator(Operator):
    bl_idname = "wm.delete_all_imported"
    bl_label = "Delete All"

    def execute(self, context):
        props = context.scene.auto_bake_props
        for obj_entry in props.imported_objects:
            obj = obj_entry.obj
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)

        # Очистка неиспользуемых данных
        for mesh in bpy.data.meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for arm in bpy.data.armatures:
            if arm.users == 0:
                bpy.data.armatures.remove(arm)
        for mat in bpy.data.materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat)

        props.imported_objects.clear()
        props.current_index = 0
        props.label_name = "None"

        self.report({'INFO'}, "All objects deleted")
        return {'FINISHED'}

# Оператор для переименования анимации
class RenameActionOperator(Operator):
    bl_idname = "wm.rename_action"
    bl_label = "Rename Animation"

    def execute(self, context):
        props = context.scene.auto_bake_props
        
        # Проверка, выбран ли объект
        if props.current_index >= len(props.imported_objects):
            self.report({'WARNING'}, "No object selected!")
            return {'CANCELLED'}

        obj = props.imported_objects[props.current_index].obj
        
        # Проверка наличия анимационных данных и действия
        if not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "Object has no animation!")
            return {'CANCELLED'}

        # Берем в качестве нового имени строчку с именем объекта
        new_name = props.label_name
        if not new_name:
            self.report({'WARNING'}, "No new name provided!")
            return {'CANCELLED'}

        # Переименование текущей анимации
        armature = props.base_armature
        if armature and armature.animation_data:
            action = armature.animation_data.action
            action.name = new_name 
        else:
            self.report({'WARNING'}, "No armature selected or no animation data available!")

        self.report({'INFO'}, f"Animation renamed to {new_name}")

        return {'FINISHED'}

# Оператор для расстановки объектов
class ArrangeOperator(Operator):
    bl_idname = "wm.arrange_objects"
    bl_label = "Arrange"

    def execute(self, context):
        props = context.scene.auto_bake_props
        armature = bpy.data.objects.get("Armature")
        if not armature:
            self.report({'WARNING'}, "Armature object not found!")
            return {'CANCELLED'}

        base_pos = armature.location.copy()
        base_pos.x += props.arrange_offset

        for obj_entry in props.imported_objects:
            obj_entry.obj.location = base_pos

        self.report({'INFO'}, "Objects arranged")
        return {'FINISHED'}

# Регистрация классов
def register():
    bpy.utils.register_class(ImportedObject)
    bpy.utils.register_class(AutoBakeProperties)
    bpy.types.Scene.auto_bake_props = PointerProperty(type=AutoBakeProperties)
    bpy.utils.register_class(AutoBake_PT_Panel)
    bpy.utils.register_class(FolderSelectOperator)
    bpy.utils.register_class(ImportFBXOperator)
    bpy.utils.register_class(ArrangeOperator)
    bpy.utils.register_class(NextModelOperator)
    bpy.utils.register_class(FinishProcessOperator)
    bpy.utils.register_class(DeleteAllImportedOperator)
    bpy.utils.register_class(RenameActionOperator)
    bpy.utils.register_class(SetPosePositionOperator)

# Удаление классов
def unregister():
    del bpy.types.Scene.auto_bake_props
    bpy.utils.unregister_class(AutoBake_PT_Panel)
    bpy.utils.unregister_class(FolderSelectOperator)
    bpy.utils.unregister_class(ImportFBXOperator)
    bpy.utils.unregister_class(ArrangeOperator)
    bpy.utils.unregister_class(NextModelOperator)
    bpy.utils.unregister_class(FinishProcessOperator)
    bpy.utils.unregister_class(DeleteAllImportedOperator)
    bpy.utils.unregister_class(RenameActionOperator)
    bpy.utils.unregister_class(AutoBakeProperties)
    bpy.utils.unregister_class(ImportedObject)
    bpy.utils.unregister_class(SetPosePositionOperator)

if __name__ == "__main__":
    register()
