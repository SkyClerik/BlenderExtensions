bl_info = {
    "name": "SCExtensions",
    "author": "SkyClerik",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "N - panel",
    "description": "Набор небольших скриптов",
    "category": "COMMUNITY",
}

import bpy  # type: ignore
import os
from bpy.types import PropertyGroup, Operator  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore
from bpy.props import (
    StringProperty,
    CollectionProperty,
    PointerProperty,
    FloatProperty,
    IntProperty,
)  # type: ignore


# ----------------- PROPERTIES -----------------
class SkyClericProperties(PropertyGroup):
    # region [place_on_the_grid]
    grid_size: bpy.props.FloatProperty(
        name="Размер ячейки",
        default=10.0,
        min=1.0
    )  # type: ignore
    offset_x: bpy.props.FloatProperty(
        name="Смещение X",
        default=1.0,
        min=0.1
    )  # type: ignore
    offset_y: bpy.props.FloatProperty(
        name="Смещение Y",
        default=1.0,
        min=0.1
    )  # type: ignore
    round_positions: bpy.props.BoolProperty(
        name="С округлением",
        description="Округлять координаты объектов до целых",
        default=False
    )  # type: ignore
    # endregion

    # region [export_selected_objects]
    export_folder: bpy.props.StringProperty(
        name="Путь сохранения",
        default="D:/Developing/ProjectManager/Data/Models/",
        subtype='DIR_PATH'
    )  # type: ignore
    # endregion

    # region [import_fbx_recursive]
    import_folder: bpy.props.StringProperty(
        name="Путь импорта",
        default="",
        subtype='DIR_PATH'
    )  # type: ignore
    # endregion


# ----------------- PANEL -----------------
class SKYCLERIC_PT_ExtensionPanel(bpy.types.Panel):
    bl_idname = "SKYCLERIC_PT_ExtensionPanel"
    bl_label = "Дополнительные методы"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Расширения"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.SkyClericProp1

        layout.operator("btn_id.first_button", text="Копировать путь до аддона", icon='CUBE')
        layout.operator("btn_id.resize_button", text="Размер = 1", icon='SCRIPT')
        layout.operator("btn_id.clear_normals", text="Очистка нормалей", icon='SCRIPT')
        layout.operator("btn_id.create_missing_uv_map", text="Создать UVMap", icon='SCRIPT')

        # region [place_on_the_grid]
        layout.separator()
        layout.label(text="Расстановка по сетке:")
        box = layout.box()
        col = box.column()

        col.prop(props, "grid_size", text="Кол-во в строке")
        row = col.row(align=True)
        row.prop(props, "offset_x", text="Ширина")
        row.prop(props, "offset_y", text="Высота")
        col.prop(props, "round_positions", text="С округлением")

        col.operator("btn_id.reset_axis_z", text="Z = 0", icon='SCRIPT')
        col.operator("btn_id.place_on_the_grid", text="Расставить по сетке", icon='GRID')
        # endregion

        # region [export_selected_objects]
        layout.separator()
        layout.label(text="Экспорт:")
        export_box = layout.box()
        export_col = export_box.column()
        export_col.prop(props, "export_folder", text="Path")
        export_col.operator("btn_id.export_selected_objects", text="Экспортировать", icon='SCRIPT')
        # endregion

        # region [import_fbx_recursive]
        layout.separator()
        layout.label(text="Импорт FBX (рекурсивно):")
        import_box = layout.box()
        import_col = import_box.column()
        row = import_col.row(align=True)
        row.prop(props, "import_folder", text="Path")
        row.operator("btn_id.select_import_folder", text="", icon='FILE_FOLDER')

        import_col.operator("btn_id.import_fbx_recursive", text="Импортировать FBX", icon='IMPORT')
        # endregion


# ----------------- OPERATORS -----------------
class SCExt_Button_Addon(bpy.types.Operator):
    bl_idname = "btn_id.first_button"
    bl_label = "Тестовая кнопка"
    bl_description = "Тестовая кнопка для проверки работы"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'INFO'}, "Тестовая кнопка активирована")
        self.show_success_message("Операция завершена")
        self.copy_addon_path_to_clipboard(context)
        return {'FINISHED'}

    def show_success_message(self, message):
        def draw(self, context):
            self.layout.label(text=message)

        bpy.context.window_manager.popup_menu(draw, title="Успех", icon='CHECKMARK')

    def copy_addon_path_to_clipboard(self, context):
        addon_path = os.path.realpath(__file__)
        context.window_manager.clipboard = addon_path
        self.report({'INFO'}, f"Путь скопирован: {addon_path}")


class Button_ReSizeObject(bpy.types.Operator):
    bl_idname = "btn_id.resize_button"
    bl_label = "Сбросить размер"
    bl_options = {'UNDO'}
    bl_description = "Сброс масштаба выделенных объектов до 1,1,1"

    def execute(self, context):
        selected = context.selected_objects
        if not selected:
            self.report({'WARNING'}, "Нет выделенных объектов")
            return {'CANCELLED'}

        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.scale = (1.0, 1.0, 1.0)
                print(f"Масштаб объекта '{obj.name}' сброшен до заводских")

        return {'FINISHED'}


class Button_PlaceOnTheGrid(bpy.types.Operator):
    bl_idname = "btn_id.place_on_the_grid"
    bl_label = "По сетке"
    bl_options = {'UNDO'}
    bl_description = "Распределить выделенные объекты по сетке"

    def execute(self, context):
        scene = context.scene
        props = scene.SkyClericProp1
        selected = context.selected_objects

        if not selected:
            self.report({'WARNING'}, "Нет выделенных объектов")
            return {'CANCELLED'}

        grid_size = props.grid_size
        offset_x = props.offset_x
        offset_y = props.offset_y
        round_flag = props.round_positions

        start_x = 0
        start_y = 0

        for i, obj in enumerate(selected):
            x = start_x + (i % grid_size) * offset_x
            y = start_y + (i // grid_size) * offset_y

            if round_flag:
                x = round(x)
                y = round(y)

            obj.location = (x, y, obj.location.z)

        self.report(
            {'INFO'},
            f"Объекты расставлены по сетке ({grid_size}x{grid_size}) {'с округлением' if round_flag else ''}"
        )

        return {'FINISHED'}


class Button_ResetAxisZ(bpy.types.Operator):
    bl_idname = "btn_id.reset_axis_z"
    bl_label = "Z = 0"
    bl_options = {'UNDO'}
    bl_description = "Установить выделенные объекты в 0 по оси Z"

    def execute(self, context):
        selected = context.selected_objects

        if not selected:
            self.report({'WARNING'}, "Нет выделенных объектов")
            return {'CANCELLED'}

        for obj in selected:
            obj.location[2] = 0

        self.report({'INFO'}, "Объекты в нулях по оси Z")
        return {'FINISHED'}


class Button_ExportSelectedObjects(bpy.types.Operator):
    bl_idname = "btn_id.export_selected_objects"
    bl_label = "Экспортировать каждый"
    bl_description = "Экспортировать выделенные объекты в указанную директорию отдельными файлами"

    def execute(self, context):
        scene = context.scene
        props = scene.SkyClericProp1

        export_folder = props.export_folder.strip()

        if not export_folder:
            self.report({'ERROR'}, "Не указан путь к папке экспорта")
            return {'CANCELLED'}

        if not os.path.exists(export_folder):
            self.report({'ERROR'}, f"Папка '{export_folder}' не существует")
            return {'CANCELLED'}

        selected = context.selected_objects

        if not selected:
            self.report({'WARNING'}, "Нет выделенных объектов")
            return {'CANCELLED'}

        # Если хочешь перед экспортом применять SCALE:
        for obj in selected:
            if obj.type != 'MESH':
                continue
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Восстанавливаем выделение для экспорта
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = selected[0]

        # Сам экспорт с "Apply Transform"
        for obj in selected:
            if obj.type != 'MESH':
                continue

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            bpy.ops.export_scene.fbx(
                filepath=os.path.join(export_folder, f"{obj.name}.fbx"),
                use_selection=True,
                apply_scale_options='FBX_SCALE_ALL',
                # ВАЖНО: это та самая галочка "Apply Transform"
                bake_space_transform=True,
                # оси как в твоём ручном пресете для Unity
                axis_forward='-Z',
                axis_up='Y',
                mesh_smooth_type='FACE',
                add_leaf_bones=False,
                use_mesh_modifiers=True,
                use_custom_props=False,
                use_tspace=True,
            )

        # Вернём выделение
        for obj in selected:
            obj.select_set(True)

        self.report({'INFO'}, "Экспорт завершен!")
        return {'FINISHED'}


class Button_ClearCustomSplitNormals(bpy.types.Operator):
    bl_idname = "btn_id.clear_normals"
    bl_label = "Очистка пользовательских нормалей"
    bl_options = {'UNDO'}
    bl_description = "Очистка пользовательских нормалей"

    def execute(self, context):
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'WARNING'}, "Нет выделенных объектов")
            return {'CANCELLED'}

        original_active = context.view_layer.objects.active
        original_mode = context.mode

        try:
            bpy.ops.ed.undo_push(message="Очистка пользовательских нормалей")

            for obj in selected_objects:
                if obj.type == 'MESH':
                    context.view_layer.objects.active = obj
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()

            self.report({'INFO'}, f"✅ Очищены нормали для {len(selected_objects)} объектов")
            print("✅ ВСЕ ОЧИЩЕНО: Пользовательские нормали удалены для всех mesh-объектов.")
            return {'FINISHED'}

        finally:
            context.view_layer.objects.active = original_active
            if original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode=original_mode)

class Button_SelectImportFolder(bpy.types.Operator):
    bl_idname = "btn_id.select_import_folder"
    bl_label = "Выбрать папку импорта"

    directory: bpy.props.StringProperty(
        name="Directory",
        subtype='DIR_PATH',
        default=""
    )

    def execute(self, context):
        props = context.scene.SkyClericProp1
        # directory всегда без завершающего слеша/бэкслеша
        props.import_folder = self.directory
        self.report({'INFO'}, f"Папка импорта: {props.import_folder}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ---------- ИМПОРТ FBX ИЗ ПАПКИ (РЕКУРСИВНО) ----------
class Button_ImportFBXRecursive(bpy.types.Operator):
    bl_idname = "btn_id.import_fbx_recursive"
    bl_label = "Импортировать FBX из папки"
    bl_description = "Рекурсивно импортировать все FBX из указанной директории"

    def execute(self, context):
        scene = context.scene
        props = scene.SkyClericProp1

        root_dir = props.import_folder.strip()

        if not root_dir:
            self.report({'ERROR'}, "Не указан путь к папке импорта")
            return {'CANCELLED'}

        if not os.path.isdir(root_dir):
            self.report({'ERROR'}, f"Папка '{root_dir}' не существует")
            return {'CANCELLED'}

        imported_count = 0

        fbx_import_args = {
            "axis_forward": "-Z",
            "axis_up": "Y",
            "use_custom_normals": True,
        }

        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if not filename.lower().endswith(".fbx"):
                    continue

                fbx_path = os.path.join(dirpath, filename)
                print(f"Импорт: {fbx_path}")
                bpy.ops.import_scene.fbx(filepath=fbx_path, **fbx_import_args)
                imported_count += 1

        self.report({'INFO'}, f"Импорт FBX завершён. Файлов: {imported_count}")
        return {'FINISHED'}

class Button_CreateMissingUV_Map(bpy.types.Operator):
    bl_idname = "btn_id.create_missing_uv_map"
    bl_label = "Создать UVMap"
    bl_description = "Создать UVMap для выделенных объектов если у объекта нет карты"

    def execute(self, context):
        # Получаем список всех выделенных объектов
        selected_objects = bpy.context.selected_objects
        
        if not selected_objects:
            self.report({'INFO'}, "LOG: Объекты не выделены. Операция отменена.")
            return {'CANCELLED'} # Исправлено: возвращаем статус

        for obj in selected_objects:
            if obj.type != 'MESH':
                self.report({'INFO'}, f"LOG: Пропуск '{obj.name}' (тип {obj.type} не является Mesh)")
                continue
            
            mesh = obj.data
            
            if not mesh.uv_layers:
                self.report({'INFO'}, f"LOG: У объекта '{obj.name}' нет UV-карт. Создаю новую...")
                try:
                    mesh.uv_layers.new(name="UVMap")
                    self.report({'INFO'}, f"SUCCESS: UV-карта успешно добавлена для '{obj.name}'")
                except Exception as e:
                    self.report({'ERROR'}, f"Не удалось создать UV-карту для '{obj.name}': {e}")
            else:
                uv_names = [layer.name for layer in mesh.uv_layers]
                self.report({'INFO'}, f"LOG: У объекта '{obj.name}' уже есть UV-карты: {uv_names}. Пропуск.")

        print("LOG: Работа скрипта завершена.")
        self.report({'INFO'}, "LOG: Работа скрипта завершена.")
        
        return {'FINISHED'} # Исправлено: обязательно возвращаем FINISHED



# ----------------- REGISTRATION -----------------
classes = (
    SkyClericProperties,
    SCExt_Button_Addon,
    Button_ReSizeObject,
    Button_PlaceOnTheGrid,
    Button_ResetAxisZ,
    Button_CreateMissingUV_Map,
    Button_ExportSelectedObjects,
    Button_ClearCustomSplitNormals,
    Button_ImportFBXRecursive,
    Button_SelectImportFolder,
    SKYCLERIC_PT_ExtensionPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.SkyClericProp1 = bpy.props.PointerProperty(type=SkyClericProperties)


def unregister():
    del bpy.types.Scene.SkyClericProp1
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
