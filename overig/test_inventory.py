import pygame
from math import ceil
# inventory view vv
from game import Entity
from components.sprite import Sprite
from components.label import Label


# player vv
from core.area import area

# inventory vv

image_path = "content/images" #aanpassen naar onze images

class ItemType:
    def __init__(self, name, icon, stack_size=1):
        self.name = name
        self.icon_name = icon
        self.icon = pygame.image.load(image_path + "/" + icon) #path nakijken
        self.stack_size = stack_size

class ItemSlot:
    def __init__(self):
        self.type = None
        self.amount = 0

class Inventory:
    def __init__(self, capacity):
        self.capacity = capacity
        self.taken_slots = 0
        self.slots = []
        for _ in range(self.capacity):
            self.slots.append(ItemSlot())
        self.listener = None
        # print(str(self))

    def notify(self):
        if self.listener is not None:
            self.listener.refresh()

    def add(self, item_type, amount=1):
        # First sweep for any open stacks
        if item_type.stack_size > 1:
            for slot in self.slots:
                if slot.type == item_type:
                    add_amo = amount
                    if add_amo > item_type.stack_size - slot.amount:
                        add_amo = item_type.stack_size - slot.amount
                    slot.amount += add_amo
                    amount -= add_amo
                    if amount <= 0:
                        self.notify()
                        return 0
        # Next, place the item in the next slot
        for slot in self.slots:
            if slot.type == None:
                slot.type = item_type
                if item_type.stack_size < amount:
                    slot.amount = item_type.stack_size
                    self.notify()
                    return self.add(item_type, amount - item_type.stack_size)
                else:
                    slot.amount = amount
                    self.notify()
                    return 0

        return amount
        
            

    def remove(self, item_type, amount=1):
        found = 0
        for slot in self.slots:
            if slot.type == item_type:
                if slot.amount < amount:
                    found += slot.amount
                    continue
                elif slot.amount == amount:
                    found += amount
                    slot.amount = 0
                    slot.type = None
                    self.notify()
                    return found
                else:
                    found += amount
                    slot.amount -= amount
                    slot.type = None
                    self.notify()
                    return found
        return found

    def has(self, item_type, amount=1):
        found = 0
        for slot in self.slots:
            if slot.type == item_type:
                found += slot.amount
                if found >= amount:
                    return True
        return False

    def get_index(self, item_type):
        for index, slot in enumerate(self.slots):
            if slot.type == item_type:
                return index
        return -1
    
    def __str__(self):
        s = ""
        for i in self.slots:
            if i.type is not None:
                s += str(i.type.name) + ": " + str(i.amount) + "\t"
            else:
                s += "Empty slot\t"
        return s
        

    def get_free_slots(self):
        return self.capacity - self.taken_slots
    
    def is_full(self):
        return self.taken_slots == self.capacity


def pick_up(item, other):                               #aanpassen naar juiste classes
    from game import Player 
    if other.has(Player):
        # inventory = other.get(Inventory)
        extra = inventory.add(item.item_type, item.quantity)
        item.quantity -= item.quantity - extra
        if item.quantity <= 0:
            from core.area import area                  #aanpassen
            area.remove_entity(item.entity)
        # print(inventory)
            

# inventory ^^
# inventory view vv

items_per_row = 5
padding_size = 5
gap_size = 5
item_size = 32

class InventoryView:
    def __init__(self, inventory, slot_image="inventory_slot.png"):     #image fixen
        self.inventory = inventory
        self.slot_image = slot_image

        width = padding_size + (items_per_row * item_size) + ((items_per_row-1 ) * gap_size) + padding_size
        rows = ceil(inventory.capacity / items_per_row)
        height = padding_size + (rows * item_size) + ((rows-1) * gap_size) + padding_size

        #from game import camera
        #x = camera.width - width
        #y = 0

        #self.window = create_window(x, y, width, height)
        self.slot_container_sprites = []
        self.slot_sprites = []

        inventory.listener = self

        self.render()

    def render(self):
        print("Called render")
        row = 0
        column = 0
        for slot in self.inventory.slots:
            x = column * (item_size + gap_size) + self.window.x + padding_size
            y = row * (item_size + gap_size) + self.window.y + padding_size
            container_sprite = Entity(Sprite(self.slot_image, True), x=x, y=y)
            self.window.get(Window).items.append(container_sprite)
            if slot.type is not None:
                print(slot.type.name)
                item_sprite = Entity(Sprite(slot.type.icon_name, True), x=x, y=y)
                if slot.type.stack_size > 1:
                    label = Entity(Label("EBGaramond-ExtraBold.ttf", str(slot.amount), color=(255, 255, 0), size=30), x=x, y=y)
                    self.window.get(Window).items.append(label)
                self.window.get(Window).items.append(item_sprite)
            column += 1
            if column >= items_per_row:
                column = 0
                row += 1


    def clear(self):
        for i in self.window.get(Window).items:
            if i.has(Sprite):
                i.get(Sprite).breakdown()
            elif i.has(Label):
                i.get(Label).breakdown()
        self.window.get(Window).items.clear()


    def refresh(self):
        self.clear()
        self.render()

    def breakdown(self):
        pass


# player vv

movement_speed = 2
inventory = Inventory(5)




class Entity:
    def __init__(self, *components, x=0, y=0):
        self.components = []
        self.x = x
        self.y = y
        for c in components:
            self.add(c)

    def add(self, component):
        component.entity = self
        self.components.append(component)

    def remove(self, kind):
        c = self.get(kind)
        if c is not None:
            c.entity = None
            self.components.remove(c)

    def has(self, kind):
        for c in self.components:
            if isinstance(c, kind):
                return True
        return False

    def get(self, kind):
        for c in self.components:
            if isinstance(c, kind):
                return c
        return None    



