bl_info = {
    "name": "Material Element Manager",
    "author": "SkyClerik",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "N-panel > Material Element Manager",
    "description": "Сохраняй и применяй UV-позиции материалов как элементы",
    "category": "UV",
}

import bpy
import bmesh
import math
from bpy.types import PropertyGroup, Operator, Panel, UIList, Menu
from bpy.props import PointerProperty, StringProperty, FloatProperty, IntProperty

addon_keymaps = []

# ======================
# ЭЛЕМЕНТ: ХРАНИЛИЩЕ ДАННЫХ
# ======================
class MaterialElement(PropertyGroup):
    material: PointerProperty(
        name="Материал",
        type=bpy.types.Material,
        description="Материал для предпросмотра"
    )
    name: StringProperty(
        name="Имя",
        default="ЭЛЕМ",
        description="Имя элемента в списке"
    )
    uv_x: FloatProperty(
        name="UV X",
        default=0.0,
        min=0.0,
        max=1.0,
        description="UV-координата X для применения"
    )
    uv_y: FloatProperty(
        name="UV Y",
        default=0.0,
        min=0.0,
        max=1.0,
        description="UV-координата Y для применения"
    )

class MATERIAL_UL_ElementList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.scale_x = 1.0

            if item.material:
                preview_icon = item.material.preview.icon_id if item.material.preview else 0
                if preview_icon:
                    row.label(text="", icon_value=preview_icon)
                else:
                    row.label(text="", icon='MATERIAL')
            else:
                row.label(text="", icon='MATERIAL')

            name_and_uv = row.row(align=True)
            name_and_uv.alignment = 'LEFT'
            name_and_uv.scale_x = 2.0

            if item.material:
                name_and_uv.label(text=item.name)
                name_and_uv.label(text=f"X: {item.uv_x:.3f} | Y: {item.uv_y:.3f}")
            else:
                name_and_uv.label(text=item.name + " (No material)")

            row.separator(factor=0.5)
            op = row.operator("element.edit", text="", icon='PREFERENCES')
            op.index = index
            
            row.separator(factor=0.5)
            op = row.operator("element.apply", text="", icon='UV')
            op.index = index
            
            row.separator(factor=0.5)
            op = row.operator("element.capture_uv", text="", icon='IMPORT')
            op.index = index

# ======================
# ОПЕРАТОР: ОТКРЫТЬ ОКНО НАСТРОЙКИ ЭЛЕМЕНТА
# ======================
class ELEMENT_OT_Edit(Operator):
    bl_idname = "element.edit"
    bl_label = "Настроить ЭЛЕМ"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if self.index >= len(scene.material_elements):
            layout.label(text="Элемент не найден", icon='ERROR')
            return
            
        element = scene.material_elements[self.index]

        layout.prop(element, "material", text="Материал")
        layout.prop(element, "name", text="Имя")
        layout.prop(element, "uv_x", text="UV X")
        layout.prop(element, "uv_y", text="UV Y")

        layout.separator()
        op = layout.operator("element.apply", text="Применить изменения")
        op.index = self.index


# ======================
# ОПЕРАТОР: ЗАПИСАТЬ UV
# ======================

class ELEMENT_OT_CaptureUV(Operator):
    bl_idname = "element.capture_uv"
    bl_label = "Записать UV из редактора"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        scene = context.scene
        if self.index >= len(scene.material_elements):
            return {'CANCELLED'}
            
        element = scene.material_elements[self.index]

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Нет активного меша")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Объект должен быть в Edit Mode")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active

        if not uv_layer:
            self.report({'ERROR'}, "Нет активного UV-слоя")
            bmesh.update_edit_mesh(mesh)
            return {'CANCELLED'}

        selected_uvs = []
        for face in bm.faces:
            if face.select:
                for loop in face.loops:
                    vert = loop.vert
                    if vert.select:
                        uv = loop[uv_layer].uv
                        selected_uvs.append(uv)

        if not selected_uvs:
            for face in bm.faces:
                if face.select:
                    for loop in face.loops:
                        uv = loop[uv_layer].uv
                        selected_uvs.append(uv)

        if not selected_uvs:
            self.report({'WARNING'}, "Нет выделенных вершин")
            bmesh.update_edit_mesh(mesh)
            return {'CANCELLED'}

        total_x = sum(uv.x for uv in selected_uvs)
        total_y = sum(uv.y for uv in selected_uvs)
        count = len(selected_uvs)

        avg_x = total_x / count
        avg_y = total_y / count

        element.uv_x = max(0, min(1, avg_x))
        element.uv_y = max(0, min(1, avg_y))

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, f"UV записаны: X={avg_x:.3f}, Y={avg_y:.3f}")
        return {'FINISHED'}

# ======================
# ПАНЕЛЬ
# ======================
class MATERIAL_ELEMENT_PT_Panel(Panel):
    bl_label = "Material Element Manager"
    bl_idname = "MATERIAL_ELEMENT_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.operator("element.add", text="Добавить ЭЛЕМ", icon='ADD')

        layout.template_list(
            "MATERIAL_UL_ElementList", "",
            scene, "material_elements",
            scene, "material_element_index"
        )

        row = layout.row()
        row.operator("element.remove", text="Удалить", icon='REMOVE')

        row = layout.row()
        row.operator("element.load_from_selection", text="Загрузить из выделенного", icon='FILE_REFRESH')

# ======================
# ОПЕРАТОР: ДОБАВИТЬ
# ======================
class ELEMENT_OT_Add(Operator):
    bl_idname = "element.add"
    bl_label = "Добавить ЭЛЕМ"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        element = scene.material_elements.add()
        element.name = f"ЭЛЕМ {len(scene.material_elements)}"
        scene.material_element_index = len(scene.material_elements) - 1
        return {'FINISHED'}

# ======================
# ОПЕРАТОР: УДАЛИТЬ
# ======================
class ELEMENT_OT_Remove(Operator):
    bl_idname = "element.remove"
    bl_label = "Удалить ЭЛЕМ"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if scene.material_element_index >= 0 and scene.material_element_index < len(scene.material_elements):
            scene.material_elements.remove(scene.material_element_index)
            if scene.material_element_index > 0:
                scene.material_element_index -= 1
            elif len(scene.material_elements) > 0:
                scene.material_element_index = 0
        return {'FINISHED'}

# ======================
# ОПЕРАТОР: ЗАГРУЗИТЬ ИЗ ВЫДЕЛЕННОГО
# ======================
class ELEMENT_OT_LoadFromSelection(Operator):
    bl_idname = "element.load_from_selection"
    bl_label = "Загрузить UV из выделенного"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Активный объект не является мешем")
            return {'CANCELLED'}
        
         # если меш линкнут/пакован из библиотеки – сделать локальным
        if obj.data and obj.data.library:
            try:
                # делает локальными объект и его данные
                bpy.ops.object.make_local(type='ALL')
            except Exception as e:
                self.report({'ERROR'}, f"Не удалось сделать объект локальным: {e}")
                return {'CANCELLED'}

        was_in_edit_mode = obj.mode == 'EDIT'
        if not was_in_edit_mode:
            bpy.ops.object.mode_set(mode='EDIT')

        try:
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active

            for face in bm.faces:
                face.select = True

            if not uv_layer:
                self.report({'ERROR'}, "Нет активного UV-слоя")
                return {'CANCELLED'}

            scene = context.scene
            scene.material_elements.clear()

            material_groups = {}

            for face in bm.faces:
                if not face.select:
                    continue
                mat_idx = face.material_index
                face_uvs = [loop[uv_layer].uv for loop in face.loops]
                if mat_idx not in material_groups:
                    material_groups[mat_idx] = []
                material_groups[mat_idx].extend(face_uvs)

            added_count = 0
            for mat_idx, uvs in material_groups.items():
                if not uvs:
                    continue

                avg_x = sum(uv.x for uv in uvs) / len(uvs)
                avg_y = sum(uv.y for uv in uvs) / len(uvs)
                avg_x = max(0.0, min(1.0, avg_x))
                avg_y = max(0.0, min(1.0, avg_y))

                material = None
                if 0 <= mat_idx < len(obj.material_slots):
                    material = obj.material_slots[mat_idx].material

                elem = scene.material_elements.add()
                elem.name = f"ЭЛЕМ_{mat_idx}" if not material else material.name
                elem.material = material
                elem.uv_x = avg_x
                elem.uv_y = avg_y
                added_count += 1

            bmesh.update_edit_mesh(mesh)

            if not was_in_edit_mode:
                bpy.ops.object.mode_set(mode='OBJECT')

            if added_count == 0:
                self.report({'WARNING'}, "Нет выделенных граней")
            else:
                self.report({'INFO'}, f"Создано {added_count} элементов")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Ошибка: {str(e)}")
            return {'CANCELLED'}
        finally:
            if obj.mode == 'EDIT':
                bmesh.update_edit_mesh(mesh)
            if not was_in_edit_mode and obj.mode == 'EDIT':
                bpy.ops.object.mode_set(mode='OBJECT')

# ======================
# ОПЕРАТОР: ELEMENT_OT_Apply
# ======================

class ELEMENT_OT_Apply(Operator):
    bl_idname = "element.apply"
    bl_label = "Применить UV"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        scene = context.scene
        if self.index < 0 or self.index >= len(scene.material_elements):
            self.report({'ERROR'}, "Неверный индекс элемента")
            return {'CANCELLED'}

        element = scene.material_elements[self.index]

        # Берём все объекты в режиме Edit Mesh
        objs = [o for o in context.objects_in_mode if o.type == 'MESH']
        if not objs:
            self.report({'WARNING'}, "Нет объектов в Edit Mode")
            return {'CANCELLED'}

        any_ok = False

        for obj in objs:
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)

            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces:
                bmesh.update_edit_mesh(mesh)
                continue

            uv_layer = bm.loops.layers.uv.active
            if not uv_layer:
                self.report({'ERROR'}, f"Нет активного UV-слоя на {obj.name}")
                bmesh.update_edit_mesh(mesh)
                continue

            for face in selected_faces:
                for loop in face.loops:
                    loop[uv_layer].uv = (element.uv_x, element.uv_y)

            bmesh.update_edit_mesh(mesh)
            any_ok = True

        if any_ok:
            self.report(
                {'INFO'},
                f"UV применены ко всем объектам в Edit Mode: X={element.uv_x}, Y={element.uv_y}"
            )
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Нет выделенных полигонов на объектах")
            return {'CANCELLED'}


# ======================
# ОПЕРАТОР: ПОКАЗАТЬ СЕТКУ С ВЫБОРОМ
# ======================

class ELEMENT_OT_GridMenuOperator(bpy.types.Operator):
    bl_idname = "element.grid_menu"
    bl_label = "Material Element Manager"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        elements = context.scene.material_elements
        count = len(elements)

        if count == 0:
            return context.window_manager.invoke_popup(self, width=150)

        # Рассчитываем количество колонок для квадратной сетки
        cols = math.ceil(math.sqrt(count))
        self.width = max(cols * 64, 32)  # не меньше 32px

        return context.window_manager.invoke_popup(self, width=self.width)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        elements = scene.material_elements

        if not elements:
            layout.label(text="Нет элементов", icon='ERROR')
            return

        # Количество колонок — то же, что и при вызове
        cols = math.ceil(math.sqrt(len(elements)))

        flow = layout.column_flow(columns=cols, align=True)
        flow.scale_y = 1.3
        flow.scale_x = 1.0

        for i, elem in enumerate(elements):
            material = elem.material
            icon = material.preview.icon_id if material and material.preview else 'MATERIAL'

            btn = flow.operator("element.apply", text="", icon_value=icon if material else 'MATERIAL')
            btn.index = i

# ======================
# РЕГИСТРАЦИЯ
# ======================
classes = (
    MaterialElement,
    MATERIAL_UL_ElementList,
    ELEMENT_OT_Edit,
    ELEMENT_OT_Apply,
    ELEMENT_OT_CaptureUV,
    ELEMENT_OT_LoadFromSelection,
    MATERIAL_ELEMENT_PT_Panel,
    ELEMENT_OT_Add,
    ELEMENT_OT_Remove,
    ELEMENT_OT_GridMenuOperator
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.material_elements = bpy.props.CollectionProperty(type=MaterialElement)
    bpy.types.Scene.material_element_index = bpy.props.IntProperty()

    wm = bpy.context.window_manager if bpy.context else None
    if wm:
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
            kmi = km.keymap_items.new(
                idname=ELEMENT_OT_GridMenuOperator.bl_idname,
                type='X',
                value='PRESS',
                ctrl=True,
                shift=True
            )
            kmi.active = True
            addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.material_elements
    del bpy.types.Scene.material_element_index

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()