bl_info = {
    "name": "Master Material Processor",          # Название аддона
    "author": "SkyClerik",         # Ваше имя
    "version": (1, 0),           # Версия
    "blender": (4, 3, 0),        # Требуемая версия Blender
    "location": "N - panel",  # Где используется
    "description": "Преобразует базовые материалы в аналог на указаной палитре",  # Описание
    "category": "COMMUNITY",       # Категория в списке аддонов
}

import bpy # type: ignore
import bmesh # type: ignore
import math
from bpy.types import PropertyGroup # type: ignore

# Добавляем свойства для настроек сетки
class SkyClericProperties(PropertyGroup):
    target_material: bpy.props.PointerProperty(
        type=bpy.types.Material,
        name="Целевой материал",
        description="Материал для замены"
    )# type: ignore

class SKYCLERIC_PT_MaterialProcessorPanel(bpy.types.Panel):
    bl_idname = "SKYCLERIC_PT_MaterialProcessorPanel"
    bl_label = "Конвертер цветов"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Конвертер"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Проверяем, существует ли группа свойств
        if hasattr(scene, "SkyClericProp2"):
            props = scene.SkyClericProp2
        else:
            props = None  # Если нет, отрисовываем предупреждение
            layout.label(text="Свойства не загружены", icon='ERROR')

        layout.separator()
        layout.label(text="Замена материалов палеткой:")
        material_box = layout.box()
        material_col = material_box.column() 

         # Проверяем, что свойства доступны
        if props:
            material_col.prop(props, "target_material")
        else:
            material_col.label(text="Свойства не загружены", icon='ERROR')  

        material_col.operator("btn_id.master_material_processor", icon='COLOR')

# Функции для преобразования RGB → CIELAB
def rgb_to_lab(rgb):
    """Преобразует RGB (0-1) в CIELAB"""
    r, g, b = rgb

    # Преобразование в XYZ
    r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4

    r = r * 100
    g = g * 100
    b = b * 100

    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505

    # Преобразование XYZ → CIELAB
    x /= 95.047
    y /= 100.000
    z /= 108.883

    if x > 0.008856:
        x = x ** (1/3)
    else:
        x = x * 7.787 + 0.13793

    if y > 0.008856:
        y = y ** (1/3)
    else:
        y = y * 7.787 + 0.13793

    if z > 0.008856:
        z = z ** (1/3)
    else:
        z = z * 7.787 + 0.13793

    L = (116 * y) - 16
    a = 500 * (x - y)
    b = 200 * (y - z)

    return (L, a, b)

def lab_distance(lab1, lab2):
    """Расстояние между цветами в CIELAB"""
    return math.sqrt(
        (lab1[0] - lab2[0])**2 +
        (lab1[1] - lab2[1])**2 +
        (lab1[2] - lab2[2])**2
    )

def find_closest_uv(palette_image, target_color):
    """Поиск ближайшего цвета в CIELAB"""
    width, height = palette_image.size
    pixels = list(palette_image.pixels[:])

    # Преобразование целевого цвета в CIELAB
    target_lab = rgb_to_lab(target_color)

    closest_dist = float('inf')
    best_uv = (0.0, 0.0)

    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            r = pixels[idx]
            g = pixels[idx+1]
            b = pixels[idx+2]
            current_color = (r, g, b)
            current_lab = rgb_to_lab(current_color)

            distance = lab_distance(target_lab, current_lab)

            if distance < closest_dist:
                closest_dist = distance
                best_uv = ((x + 0.5)/width, (y + 0.5)/height)

    return best_uv

def replace_material_and_shrink_uv(old_prefix, new_mat_name, uv_x, uv_y):
    initial_mode = bpy.context.mode
    selected_objects = bpy.context.selected_objects

    total_objects = len(selected_objects)
    current_object = 0

    if total_objects > 0:
        bpy.context.window_manager.progress_begin(0, total_objects)

    for obj in selected_objects:
        if obj.type == 'MESH':
            current_object += 1
            bpy.context.window_manager.progress_update(current_object)

            active_slot_index = obj.active_material_index
            target_slots = []

            # Ищем слоты с исходным материалом, исключая уже замененные
            for slot in obj.material_slots:
                if slot.material:
                    base_name = slot.material.name.split('.')[0]
                    if base_name == old_prefix and slot.material.name != new_mat_name:
                        target_slots.append(slot)

            if not target_slots:
                continue

            # Переключение в режим редактирования
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')

            # Выделяем полигоны для всех целевых слотов
            for slot in target_slots:
                obj.active_material_index = slot.slot_index
                bpy.ops.object.material_slot_select()

            # Обработка UV
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.active

            if not uv_layer:
                print(f"Ошибка: У объекта '{obj.name}' нет UV-слоя!")
                continue

            for face in bm.faces:
                if face.select:
                    for loop in face.loops:
                        loop[uv_layer].uv = (uv_x, uv_y)

            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Замена материалов
            new_mat = bpy.data.materials.get(new_mat_name)
            if not new_mat:
                print(f"Ошибка: Материал '{new_mat_name}' не найден!")
                continue

            for slot in target_slots:
                slot.material = new_mat

            obj.active_material_index = active_slot_index

    if total_objects > 0:
        bpy.context.window_manager.progress_end()

    # Возвращение в исходный режим
    if selected_objects:
        bpy.context.view_layer.objects.active = selected_objects[0]
    bpy.ops.object.mode_set(mode=initial_mode)
    for obj in selected_objects:
        obj.select_set(True)

class MasterMaterialProcessor(bpy.types.Operator):
    bl_idname = "btn_id.master_material_processor"
    bl_label = "Автоматическая обработка материалов"
    bl_options = {'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.SkyClericProp2
        target_material = props.target_material        
        selected = context.selected_objects

        if not selected:
            self.report({'ERROR'}, "Нет выделенных объектов")
            return {'CANCELLED'}

        if not target_material:
            self.report({'ERROR'}, "Не выбран целевой материал")
            return {'CANCELLED'}

        # Извлечение изображения палитры
        palette_image = None
        if target_material.node_tree:
            for node in target_material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    palette_image = node.image
                    break

        if not palette_image:
            self.report({'ERROR'}, "В целевом материале нет Image Texture")
            return {'CANCELLED'}

        # Сбор уникальных цветов
        materials_rgb = {}
        for obj in selected:
            for slot in obj.material_slots:
                if slot.material:
                    mat = slot.material
                    base_name = mat.name.split('.')[0]

                    principled_node = next(
                        (n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'),
                        None
                    )

                    if not principled_node:
                        self.report({'WARNING'}, f"У материала '{mat.name}' нет Principled BSDF, он не будет обработан")
                        continue

                    color = principled_node.inputs['Base Color'].default_value[:3]
                    materials_rgb[base_name] = color

        if not materials_rgb:
            self.report({'ERROR'}, "Нет материалов с Principled BSDF для обработки")
            return {'CANCELLED'}

        # Поиск UV-координат
        uv_positions = {}
        for base_name, target_color in materials_rgb.items():
            best_uv = find_closest_uv(palette_image, target_color)
            uv_positions[base_name] = best_uv

        # Замена материалов и UV
        total_materials = len(uv_positions)
        current_material = 0

        for base_name, (u, v) in uv_positions.items():
            current_material += 1
            self.report({'INFO'}, f"Обработка {base_name} ({current_material}/{total_materials})")
            replace_material_and_shrink_uv(base_name, target_material.name, u, v)

        # Очистка дубликатов
        total_objects = len(selected)
        current_object = 0
        for obj in selected:
            if obj.type == 'MESH':
                current_object +=1
                self.report({'INFO'}, f"Очистка дубликатов у {obj.name} ({current_object}/{total_objects})")
                unique_mats = []
                existing = set()
                for slot in obj.material_slots:
                    if slot.material and slot.material not in existing:
                        existing.add(slot.material)
                        unique_mats.append(slot.material)
                obj.data.materials.clear()
                for mat in unique_mats:
                    obj.data.materials.append(mat)

        # Итоговый отчёт
        output = []
        for name, (u, v) in uv_positions.items():
            r, g, b = materials_rgb[name]
            output.append(f"{name} - UV: ({u:.4f}, {v:.4f}) | RGB: ({r:.2f}, {g:.2f}, {b:.2f})")

        self.report({'INFO'}, "\n".join(output))
        print("Обработка завершена:")
        for line in output:
            print(line)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

# region [REGISTRATION]
def register():
    bpy.utils.register_class(SkyClericProperties)  
    bpy.types.Scene.SkyClericProp2 = bpy.props.PointerProperty(type=SkyClericProperties)
    bpy.utils.register_class(MasterMaterialProcessor)
    bpy.utils.register_class(SKYCLERIC_PT_MaterialProcessorPanel)

def unregister():
    del bpy.types.Scene.SkyClericProp2  
    bpy.utils.unregister_class(SkyClericProperties)
    bpy.utils.unregister_class(SKYCLERIC_PT_MaterialProcessorPanel)
    bpy.utils.unregister_class(MasterMaterialProcessor)
# endregion

if __name__ == "__main__":
    register()