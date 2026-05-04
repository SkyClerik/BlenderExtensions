bl_info = {
    "name": "UV Color Picker",          # Название аддона
    "author": "SkyClerik",         # Ваше имя
    "version": (1, 0),           # Версия
    "blender": (4, 3, 0),        # Требуемая версия Blender
    "location": "Ahader Editor > N - panel",  # Где используется
    "description": "Поиск цвета на палетке",  # Описание
    "category": "COMMUNITY",       # Категория в списке аддонов
}

import bpy  # type: ignore
import math
import time
import colorsys
from bpy.types import Operator, Panel, PropertyGroup  # type: ignore
from bpy.props import StringProperty, FloatProperty, IntProperty, FloatVectorProperty, PointerProperty, BoolProperty, CollectionProperty  # type: ignore
from mathutils import Vector # type: ignore

# Класс для хранения информации о найденном цвете и UV
class FoundColorItem(PropertyGroup):
    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0
    )  # type: ignore
    uv_coords: FloatVectorProperty(name="UV", size=2, default=(0.0, 0.0))  # type: ignore
# Класс настроек
class UVColorSettings(PropertyGroup):
    color_picker: bpy.props.FloatVectorProperty(
        name="Цвет",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),  # Белый цвет по умолчанию
        min=0.0,
        max=1.0,
        description="Выберите цвет для поиска UV-координат"
    )  # type: ignore
    last_uv: FloatVectorProperty(
        name="Последняя UV",
        size=2,
        description="UV-координата последнего найденного пикселя"
    )  # type: ignore
    show_history: BoolProperty(
        name="Показать историю",
        default=False,
        description="Показать/скрыть историю найденных цветов"
    )  # type: ignore
    history_data: StringProperty(
        name="История данных",
        default="",
        description="Сохранённая история цветов в виде строки"
    )  # type: ignore
    found_colors: CollectionProperty(type=FoundColorItem)  # type: ignore

# Класс настроек для поиска цвета
class ColorSearchSettings(PropertyGroup):
    hue_weight: FloatProperty(
        name="Вес оттенка", # Hue Weight
        description= "Вес компонента оттенка в HSV", # "Weight for Hue component in HSV",
        default=0.4,
        min=0.0,
        max=1.0,
        precision=2
    )  # type: ignore
    saturation_weight: FloatProperty(
        name="Вес насыщенности", # Saturation Weight
        description="Вес компонента насыщенности в HSV", # Weight for Saturation component in HSV
        default=0.1,
        min=0.0,
        max=1.0,
        precision=2
    )  # type: ignore
    value_weight: FloatProperty(
        name="Вес значения", # Value Weight
        description="Вес компонента «Значение» в HSV", # Weight for Value component in HSV
        default=0.5,
        min=0.0,
        max=1.0,
        precision=2
    )  # type: ignore
    step: IntProperty(
        name="Шаг поиска", # Step Size
        description="Шаг выборки пикселей для более быстрого поиска", # Pixel sampling step for faster search
        default=10,
        min=1,
        max=50
    )  # type: ignore
    threshold: FloatProperty(
        name="Порог", # Threshold
        description="Максимальный порог цветового различия", # Maximum color difference threshold
        default=0.5,
        min=0.0,
        max=1.0,
        precision=2
    )  # type: ignore
    is_collapsed: BoolProperty(
        name="Настройки", # Collapse Settings
        description="Переключить видимость настроек поиска цвета", # Toggle visibility of color search settings
        default=True
    )  # type: ignore

# Оператор для очистки списка истории
class ClearColorHistoryOperator(Operator):
    bl_idname = "node.clear_color_history"
    bl_label = "Очистить историю"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.uv_color_settings
        settings.found_colors.clear()
        self.report({'INFO'}, "История цветов очищена")
        return {'FINISHED'}
    
# Оператор для удаления конкретного элемента из истории
class RemoveColorHistoryItemOperator(Operator):
    bl_idname = "node.remove_color_history_item"
    bl_label = "Удалить элемент"
    bl_options = {'REGISTER'}
    
    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        settings = context.scene.uv_color_settings
        if 0 <= self.index < len(settings.found_colors):
            settings.found_colors.remove(self.index)
            self.report({'INFO'}, "Элемент удален из истории")
        else:
            self.report({'WARNING'}, "Ошибка: элемент не найден")
        return {'FINISHED'}
    
# Операторы для копирования UV X и Y из истории
class CopyHistoryUVXOperator(Operator):
    bl_idname = "node.copy_history_uv_x"
    bl_label = "Копировать UV X"
    bl_options = {'REGISTER'}
    
    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        settings = context.scene.uv_color_settings
        if 0 <= self.index < len(settings.found_colors):
            uv_x = settings.found_colors[self.index].uv_coords[0]
            bpy.context.window_manager.clipboard = str(uv_x)
            self.report({'INFO'}, f"UV X ({uv_x:.4f}) скопирован в буфер обмена")
        else:
            self.report({'WARNING'}, "Ошибка: элемент не найден")
        return {'FINISHED'}

class CopyHistoryUVYOperator(Operator):
    bl_idname = "node.copy_history_uv_y"
    bl_label = "Копировать UV Y"
    bl_options = {'REGISTER'}
    
    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        settings = context.scene.uv_color_settings
        if 0 <= self.index < len(settings.found_colors):
            uv_y = settings.found_colors[self.index].uv_coords[1]
            bpy.context.window_manager.clipboard = str(uv_y)
            self.report({'INFO'}, f"UV Y ({uv_y:.4f}) скопирован в буфер обмена")
        else:
            self.report({'WARNING'}, "Ошибка: элемент не найден")
        return {'FINISHED'}

class FindColorUVOperator(Operator):
    bl_idname = "node.find_color_uv"
    bl_label = "Найти цвет на палетке"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        settings = scene.uv_color_settings
        search_settings = scene.color_search_settings 
        target_color = settings.color_picker  # Получаем цвет как RGB (кортеж из 3 значений 0.0-1.0)
        
        # Сначала проверяем, есть ли цвет в истории
        for item in settings.found_colors:
            if rgb_distance(item.color, target_color) < 0.01:  # Сравниваем цвета с небольшой погрешностью
                settings.last_uv = item.uv_coords
                self.report({'INFO'}, f"UV из истории: ({item.uv_coords[0]:.4f}, {item.uv_coords[1]:.4f})")
                return {'FINISHED'}
        
        # Если цвет не найден в истории, ищем на текстуре
        obj = context.object
        if not obj or not obj.active_material:
            self.report({'ERROR'}, "Выберите объект с материалом")
            return {'CANCELLED'}
        
        material = obj.active_material
        active_node = material.node_tree.nodes.active
        if active_node.type != 'TEX_IMAGE' or not active_node.image:
            self.report({'ERROR'}, "Активная нода должна быть Image Texture с изображением")
            return {'CANCELLED'}
        
        image = active_node.image
        
        bpy.context.window_manager.progress_begin(0, 100)
         # Получаем настройки из UI
        weights = (search_settings.hue_weight, search_settings.saturation_weight, search_settings.value_weight)
        step = search_settings.step
        threshold = search_settings.threshold
        # Вызываем функцию поиска с параметрами из UI
        closest_uv = find_closest_uv(image, target_color, step=step, threshold=threshold, weights=weights)
        bpy.context.window_manager.progress_end()
        
        if closest_uv:
            settings.last_uv = closest_uv
            # Добавляем в историю, если цвет не был найден ранее
            new_item = settings.found_colors.add()
            new_item.color = target_color
            new_item.uv_coords = closest_uv
            save_history_to_string(context)  # Сохраняем историю после добавления
            self.report({'INFO'}, f"UV: ({closest_uv[0]:.4f}, {closest_uv[1]:.4f})")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Пиксель не найден")
            return {'CANCELLED'}
# Операторы для копирования UV X и Y для текущего результата
class CopyUVXOperator(Operator):
    bl_idname = "node.copy_uv_x"
    bl_label = "Копировать UV X"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.uv_color_settings
        if settings.last_uv[0] != 0.0:
            bpy.context.window_manager.clipboard = str(settings.last_uv[0])
            self.report({'INFO'}, "UV X скопирован в буфер обмена")
        else:
            self.report({'WARNING'}, "Нет данных UV для копирования")
        return {'FINISHED'}

class CopyUVYOperator(Operator):
    bl_idname = "node.copy_uv_y"
    bl_label = "Копировать UV Y"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.uv_color_settings
        if settings.last_uv[1] != 0.0:
            bpy.context.window_manager.clipboard = str(settings.last_uv[1])
            self.report({'INFO'}, "UV Y скопирован в буфер обмена")
        else:
            self.report({'WARNING'}, "Нет данных UV для копирования")
        return {'FINISHED'}
# Операторы для шаблонных настроек
class SetHuePriorityOperator(Operator):
    bl_idname = "node.set_hue_priority"
    bl_label = "Приоритет оттенка" # "Hue Priority"
    bl_description = "Установите веса с приоритетом на оттенок" # Set weights with priority on Hue
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.color_search_settings
        settings.hue_weight = 0.7
        settings.saturation_weight = 0.1
        settings.value_weight = 0.2
        return {'FINISHED'}

class SetValuePriorityOperator(Operator):
    bl_idname = "node.set_value_priority"
    bl_label = "Приоритет значения" # "Value Priority"
    bl_description = "Установите веса с приоритетом на значение" # Set weights with priority on Value
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.color_search_settings
        settings.hue_weight = 0.2
        settings.saturation_weight = 0.1
        settings.value_weight = 0.7
        return {'FINISHED'}

class SetBalancedOperator(Operator):
    bl_idname = "node.set_balanced"
    bl_label = "Сбалансированный" # "Balanced"
    bl_description = "Установить сбалансированные веса для HSV" # Set balanced weights for HSV
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.color_search_settings
        settings.hue_weight = 0.4
        settings.saturation_weight = 0.2
        settings.value_weight = 0.4
        return {'FINISHED'}

class SetSaturationPriorityOperator(Operator):
    bl_idname = "node.set_saturation_priority"
    bl_label = "Приоритет насыщенности" # "Saturation Priority"
    bl_description = "Установить веса с приоритетом насыщения" # Set weights with priority on Saturation
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.color_search_settings
        settings.hue_weight = 0.3
        settings.saturation_weight = 0.5
        settings.value_weight = 0.2
        return {'FINISHED'}
# Обновленная панель с историей и кнопкой удаления
class UVColorPanel(Panel):
    bl_label = "UV Поиск по цвету"
    bl_idname = "NODE_PT_uv_color_picker"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "UV Color Picker"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.uv_color_settings

        # Основные элементы
        layout.label(text="Параметры поиска", icon='PREFERENCES')
        # Поле для выбора цвета с помощью ColorPicker (включает HEX-ввод и пипетку)
        layout.prop(settings, "color_picker", text="Цвет")
        # Кнопка для поиска UV-координат        
        layout.operator("node.find_color_uv", icon='EYEDROPPER')

        # Настройки поиска цвета
        layout.separator()
        search_settings = scene.color_search_settings
        row_1 = layout.row()
        row_1.prop(search_settings, "is_collapsed", icon='TRIA_DOWN' if not search_settings.is_collapsed else 'TRIA_RIGHT', emboss=False)
        row_1.label(text="Настройки поиска цвета")

        if not search_settings.is_collapsed:
            box = layout.box()
            # Слайдеры для весов HSV
            box.prop(search_settings, "hue_weight", slider=True)
            box.prop(search_settings, "saturation_weight", slider=True)
            box.prop(search_settings, "value_weight", slider=True)
            # Слайдеры для шага и порога
            box.prop(search_settings, "step", slider=True)
            box.prop(search_settings, "threshold", slider=True)
            # Кнопки для шаблонов
            grid = box.grid_flow(columns=2, align=True)
            grid.operator("node.set_hue_priority")
            grid.operator("node.set_value_priority")
            grid.operator("node.set_balanced")
            grid.operator("node.set_saturation_priority")

        # Результат
        if settings.last_uv[0] != 0.0 or settings.last_uv[1] != 0.0:
            box = layout.box()
            box.label(text=f"UV-координата:", icon='UV_DATA')
            box.label(text=f"({settings.last_uv[0]:.4f}, {settings.last_uv[1]:.4f})")
            row = box.row(align=True)
            row.operator("node.copy_uv_x", text="Копировать X", icon='COPYDOWN')
            row.operator("node.copy_uv_y", text="Копировать Y", icon='COPYDOWN')

        # История найденных цветов
        layout.separator()
        row = layout.row()
        row.prop(settings, "show_history", icon='STATUSBAR')
        
        if settings.show_history:
            box = layout.box()
            box.label(text="История цветов:", icon='COLOR')
            if len(settings.found_colors) > 0:
                for i, item in enumerate(settings.found_colors):
                    col = box.column(align=True)

                    color_row = col.row(align=True)
                    color_row.label(text=f"UV: ({item.uv_coords[0]:.4f}, {item.uv_coords[1]:.4f})")
                    color_row.prop(item, "color", text="")

                    row = col.row(align=True)
                    op_x = row.operator("node.copy_history_uv_x", text="Копировать X", icon='COPYDOWN')
                    op_x.index = i
                    op_y = row.operator("node.copy_history_uv_y", text="Копировать Y", icon='COPYDOWN')
                    op_y.index = i
                    op_remove = row.operator("node.remove_color_history_item", text="", icon='X')
                    op_remove.index = i
                box.operator("node.clear_color_history", icon='TRASH')
            else:
                box.label(text="История пуста", icon='INFO')

        # ДОКУМЕНТАЦИЯ
        layout.separator()
        box = layout.box()
        box.label(text="Как использовать:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Укажите искомый цвет")
        col.label(text="2. Выделите ноду с текстурой считаемой цветовой палитрой'")
        col.label(text="❗ Изображение должно быть загружено в ноде")
        col.label(text="3. Нажмите кнопку 'Найти UV по цвету'")
        col.label(text="Найденный цвет запишется в историю цветов. Поиск сперва ищет в истории а потом на текстуре. История не дублирует цвета.")

# Функции для работы с цветами и поиском
def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))

# Вспомогательная функция для конвертации RGB в HEX
def rgb_to_hex(rgb):
    r, g, b = [int(c * 255) for c in rgb]
    return f"#{r:02x}{g:02x}{b:02x}".upper()

def rgb_distance(rgb1: tuple, rgb2: tuple) -> float:
    return math.sqrt(sum((a - b)**2 for a, b in zip(rgb1, rgb2)))

def rgb_to_hsv(r, g, b):
    """Конвертация RGB в HSV с помощью colorsys."""
    return colorsys.rgb_to_hsv(r, g, b)

def hsv_distance(hsv1: tuple, hsv2: tuple, weights: tuple = (0.4, 0.1, 0.5)) -> float:
    """Вычисление расстояния между двумя цветами в HSV с учётом весов.
    weights: (hue_weight, saturation_weight, value_weight)"""
    h1, s1, v1 = hsv1
    h2, s2, v2 = hsv2
    
    # Учитываем циклическую природу оттенка (hue)
    h_diff = min(abs(h1 - h2), 1.0 - abs(h1 - h2)) * 2.0
    s_diff = abs(s1 - s2)
    v_diff = abs(v1 - v2)
    
    # Применяем веса
    return (h_diff * weights[0]) + (s_diff * weights[1]) + (v_diff * weights[2])

def find_closest_uv(image, target_color: tuple, step: int = 1, threshold: float = 1.0, weights: tuple = (0.4, 0.1, 0.5)) -> tuple:
    """Поиск ближайшего UV-координат к заданному цвету с использованием HSV.
    Args:
        image: Объект изображения в Blender.
        target_color: Цвет в формате RGB (tuple of 3 floats).
        step: Шаг выборки пикселей для оптимизации (1 = проверять все пиксели).
        threshold: Максимально допустимая разница цвета (если больше, результат не возвращается).
        weights: Веса для компонентов HSV (hue, saturation, value).
    Returns:
        UV-координаты (tuple of 2 floats) или None, если подходящий цвет не найден.
    """
    if not image or image.size[0] == 0 or image.size[1] == 0:
        return None
    
    width, height = image.size
    total_pixels = width * height
    progress_step = max(1, total_pixels // 100)
    
    closest_distance = float('inf')
    closest_uv = (0.0, 0.0)
    
    # Конвертируем искомый цвет в HSV
    target_hsv = rgb_to_hsv(*target_color)
    
    start_time = time.time()
    
    for y in range(0, height, step):
        for x in range(0, width, step):
            pixel_index = (y * width + x) * 4
            r = image.pixels[pixel_index]
            g = image.pixels[pixel_index + 1]
            b = image.pixels[pixel_index + 2]
            current_hsv = rgb_to_hsv(r, g, b)
            
            distance = hsv_distance(current_hsv, target_hsv, weights)
            
            if distance < closest_distance:
                closest_distance = distance
                uv_x = (x + 0.5) / width
                uv_y = (y + 0.5) / height
                closest_uv = (uv_x, uv_y)
            
            if (y * width + x) % progress_step == 0:
                progress = (y * width + x) / total_pixels
                bpy.context.window_manager.progress_update(progress * 100)
    
    elapsed_time = time.time() - start_time
    print(f"Поиск завершён за {elapsed_time:.1f} сек")
    
    # Проверяем, укладывается ли минимальная разница в порог
    if closest_distance > threshold:
        print(f"Цвет не найден: минимальная разница {closest_distance} превышает порог {threshold}")
        return None
        
    return closest_uv

def on_load_post(dummy):
    load_history_from_string(bpy.context)

def on_save_pre(dummy):
    save_history_to_string(bpy.context)

def save_history_to_string(context):
    settings = context.scene.uv_color_settings
    history = []
    for item in settings.found_colors:
        history.append(f"{item.color[0]},{item.color[1]},{item.color[2]};{item.uv_coords[0]};{item.uv_coords[1]}")
    settings.history_data = "|".join(history)

def load_history_from_string(context):
    settings = context.scene.uv_color_settings
    settings.found_colors.clear()
    if settings.history_data:
        history = settings.history_data.split("|")
        for entry in history:
            if entry:
                color_data, uv_x, uv_y = entry.split(";")
                r, g, b = map(float, color_data.split(","))
                new_item = settings.found_colors.add()
                new_item.color = (r, g, b)
                new_item.uv_coords[0] = float(uv_x)
                new_item.uv_coords[1] = float(uv_y)

def register():
    try:
        # Сначала регистрируем классы, которые используются в других классах
        bpy.utils.register_class(FoundColorItem)
        bpy.utils.register_class(UVColorSettings)
        bpy.types.Scene.uv_color_settings = PointerProperty(type=UVColorSettings)
        # Добавляем настройки поиска цвета
        bpy.utils.register_class(ColorSearchSettings)
        bpy.types.Scene.color_search_settings = PointerProperty(type=ColorSearchSettings)

        bpy.utils.register_class(FindColorUVOperator)
        bpy.utils.register_class(CopyUVXOperator)
        bpy.utils.register_class(CopyUVYOperator)
        bpy.utils.register_class(CopyHistoryUVXOperator)
        bpy.utils.register_class(CopyHistoryUVYOperator)
        bpy.utils.register_class(ClearColorHistoryOperator)
        bpy.utils.register_class(RemoveColorHistoryItemOperator)
        # Регистрируем операторы для шаблонов
        bpy.utils.register_class(SetHuePriorityOperator)
        bpy.utils.register_class(SetValuePriorityOperator)
        bpy.utils.register_class(SetBalancedOperator)
        bpy.utils.register_class(SetSaturationPriorityOperator)
        bpy.utils.register_class(UVColorPanel)
        bpy.app.handlers.load_post.append(on_load_post)
        bpy.app.handlers.save_pre.append(on_save_pre)

        print("Аддон UV Color Picker успешно зарегистрирован")
    except Exception as e:
        print(f"Ошибка при регистрации аддона: {e}")

def unregister():
    try:
        # Удаляем свойства из Scene
        if hasattr(bpy.types.Scene, "uv_color_settings"):
            del bpy.types.Scene.uv_color_settings
        if hasattr(bpy.types.Scene, "color_search_settings"):
            del bpy.types.Scene.color_search_settings

        # Отменяем регистрацию классов в обратном порядке
        bpy.utils.unregister_class(UVColorPanel)
        bpy.utils.unregister_class(SetSaturationPriorityOperator)
        bpy.utils.unregister_class(SetBalancedOperator)
        bpy.utils.unregister_class(SetValuePriorityOperator)
        bpy.utils.unregister_class(SetHuePriorityOperator)
        bpy.utils.unregister_class(RemoveColorHistoryItemOperator)
        bpy.utils.unregister_class(ClearColorHistoryOperator)
        bpy.utils.unregister_class(CopyHistoryUVYOperator)
        bpy.utils.unregister_class(CopyHistoryUVXOperator)
        bpy.utils.unregister_class(CopyUVYOperator)
        bpy.utils.unregister_class(CopyUVXOperator)
        bpy.utils.unregister_class(FindColorUVOperator)
        bpy.utils.unregister_class(ColorSearchSettings)
        bpy.utils.unregister_class(UVColorSettings)
        bpy.utils.unregister_class(FoundColorItem)
        bpy.app.handlers.load_post.remove(on_load_post)
        bpy.app.handlers.save_pre.remove(on_save_pre)

        print("Аддон UV Color Picker успешно удален")
    except Exception as e:
        print(f"Ошибка при удалении аддона: {e}")


if __name__ == "__main__":
    register()
