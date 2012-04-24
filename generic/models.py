# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Author: Mathijs Dumon
# This work is licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License. 
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/3.0/ or send
# a letter to Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.

import matplotlib
import matplotlib.transforms as transforms

import numpy as np

from gtkmvc import Observable
from gtkmvc.model import Model, Signal, ListStoreModel
from gtkmvc.support.metaclasses import ObservablePropertyMeta

from generic.treemodels import XYListStore
from generic.io import Storable, PyXRDDecoder
from generic.utils import smooth

def add_cbb_props(*props):
    props, mappers, callbacks = zip(*props)
    prop_dict = dict(zip(props, zip(mappers, callbacks)))

    @Model.getter(*props)
    def get_cbb_prop(self, prop_name):
        return getattr(self, "_%s" % prop_name)
    @Model.setter(*props)
    def set_cbb_prop(self, prop_name, value):
        value = prop_dict[prop_name][0](value)
        if value in getattr(self, "_%ss" % prop_name): 
            setattr(self, "_%s" % prop_name, value)
            callback = prop_dict[prop_name][1]
            if callable(callback):
                prop_dict[prop_name][1](self, prop_name, value)
        else:
            raise ValueError, "'%s' is not a valid value for %s!" % (value, prop_name)

class CSVMixin():
    
    __csv_storables__ = [] #list of tuples "label", "property_name"

    @classmethod
    def save_as_csv(type, filename, items):
        import csv
        atl_writer = csv.writer(open(filename, 'wb'), delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)      
        labels, props = zip(*type.__csv_storables__)
        atl_writer.writerow(labels)
        for item in items:
            prop_row = []
            for prop in props:
                prop_row.append(getattr(item, prop))
            atl_writer.writerow(prop_row)
           
    @classmethod 
    def get_from_csv(type, filename, callback = None):
        import csv
        atl_reader = csv.reader(open(filename, 'rb'), delimiter=',', quotechar='"')
        labels, props = zip(*type.__csv_storables__)
        header = True
        items = []
        for row in atl_reader:
            if not header:
                kwargs = dict()
                for i, prop in enumerate(props):
                    kwargs[prop] = row[i]
                new_item = type(**kwargs)
                if callback is not None and callable(callback):
                    callback(new_item)
                items.append(new_item)
            header = False
        return items
    
    pass #end of class

class ObjectListStoreChildMixin():
    
    __list_store__ = None
        
    def liststore_item_changed(self):
        if self.__list_store__ != None:
            self.__list_store__.on_item_changed(self)
            
    pass #end of class

class ChildModel(Model):

    #MODEL INTEL:
    __have_no_widget__ = ["parent", "removed", "added"]
    __observables__ = __have_no_widget__
    __parent_alias__ = None

    #SIGNALS:
    removed = None
    added = None

    #PROPERTIES:
    _parent = None
    def get_parent_value(self): return self._parent
    def set_parent_value(self, value):
        self._unattach_parent()
        self._parent = value
        self._attach_parent()

    def __init__(self, parent=None):
        Model.__init__(self)
        self.removed = Signal()
        self.added = Signal()
        
        self.parent = parent
        if self.__parent_alias__ != None:
            setattr(self.__class__, self.__parent_alias__, property(lambda self: self.parent)) 

    # ------------------------------------------------------------
    #      Methods & Functions
    # ------------------------------------------------------------       
    def _unattach_parent(self):
        if self.parent != None:
            self.removed.emit()
    
    def _attach_parent(self):
        if self.parent != None:
            self.added.emit()
            
    pass #end of class

class XYData(ChildModel, Storable, Observable):

    #MODEL INTEL:
    __temporarals__ = [
        "plot_update",
        "display_offset", 
        "bg_position", "bg_scale", "bg_pattern", "bg_type", 
        "sd_degree", "sd_type", 
        "shift_value", "shift_position"
    ]
    
    __observables__ = __temporarals__ + [
        "data_name", "data_label", 
        "xy_data"
    ]
    __parent_alias__ = 'specimen'
    __storables__ = [val for val in __observables__ if not val in __temporarals__ ] + ["color",]

    #SIGNALS:
    plot_update = None

    #PROPERTIES:
    xy_empty_data = ([0,0],[0,0])
    line = None
    
    xy_data = None

    _data_name = "XYData"    
    def get_data_name_value(self): return self._data_name
    def set_data_name_value(self, value):
        self._data_name = str(value)
        self.line.set_label(self.data_label)

    _data_label = "%(name)s"
    def get_data_label_value(self): return self._data_label % { 'name': self._data_name }
    def set_data_label_value(self, value):
        self._data_label = str(value)
        self.line.set_label(self.data_label)
    
    _display_offset = 0
    def get_display_offset_value(self): return self._display_offset
    def set_display_offset_value(self, value):
        self._display_offset = float(value)
        self.plot_update.emit()
        
    _bg_position = 0
    bg_line = None
    def get_bg_position_value(self): return self._bg_position
    def set_bg_position_value(self, value):
        self._bg_position = float(value)
        self.plot_update.emit()

    _bg_scale = 1.0
    def get_bg_scale_value(self): return self._bg_scale
    def set_bg_scale_value(self, value):
        self._bg_scale = float(value)
        self.plot_update.emit()
            
    _bg_pattern = None
    def get_bg_pattern_value(self): return self._bg_pattern
    def set_bg_pattern_value(self, value):
        self._bg_pattern = value
        self.plot_update.emit()

    _sd_degree = 0
    sd_data = None
    sd_line = None
    def get_sd_degree_value(self): return self._sd_degree
    def set_sd_degree_value(self, value):
        self._sd_degree = float(value)
        self.try_smooth_data()
        self.plot_update.emit()

    _shift_value = 0.0
    shifted_line = None
    reference_line = None
    def get_shift_value_value(self): return self._shift_value
    def set_shift_value_value(self, value):
        self._shift_value = float(value)
        self.plot_update.emit()

    _shift_position = 0.42574
    _shift_positions = { 
        0.42574: "Quartz\t(SiO2)",
        0.3134: "Silicon\t(Si)",
        0.2476: "Zincite\t(ZnO)",
        0.2085: "Corundum\t(Al2O3)"
    }    
    def on_shift(self, prop_name, value):
        self.find_shift_value()

    _sd_type = 0
    _sd_types = { 0: "Moving Triangle" } #TODO add more types  

    _bg_type = 0
    _bg_types = { 0: "Linear", 1: "Pattern" } #TODO add more types
    def get_bg_type_lbl(self):
        return self._bg_types[self._bg_type]    
    def on_bgtype(self, prop_name, value):
        self.find_bg()
           
    add_cbb_props(("shift_position", float, on_shift), ("sd_type", int, None), ("bg_type", int, on_bgtype))
               
    @property
    def color(self):
        return self.line.get_color()
    @color.setter
    def color(self, color):
        if self.color != color:
            self.line.set_color(color)
            if self.line.get_visible() and self.line.get_axes() != None:
                self.plot_update.emit()
    
    # ------------------------------------------------------------
    #      Initialisation and other internals
    # ------------------------------------------------------------
    def __init__(self, data_name=None, data_label=None, xy_data=None, color="#0000FF", parent=None, **kwargs):
        ChildModel.__init__(self, parent=parent)
        Storable.__init__(self)
        Observable.__init__(self)
        
        self.plot_update = Signal()
        
        self._data_name = data_name or self._data_name
        self._data_label = data_label or self._data_label
        self.line = matplotlib.lines.Line2D(*self.xy_empty_data, label=self.data_label, color=color, aa=True)
        self.xy_data = xy_data or XYListStore()
        
        self.update_data()
    
    # ------------------------------------------------------------
    #      Input/Output stuff
    # ------------------------------------------------------------    
    @staticmethod
    def from_json(data_name=None, data_label=None, xy_data=None, color=None, **kwargs):
        xy_data = PyXRDDecoder().__pyxrd_decode__(xy_data)
        return XYData(data_name=data_name, data_label=data_label, xy_data=xy_data, color=color)
            
    def save_data(self, filename):
        f = open(filename, 'w')
        f.write("%s %s\n" % (self.parent.data_name, self.parent.data_sample))
        np.savetxt(f, zip(self.xy_data._model_data_x, self.xy_data._model_data_y), fmt="%.8f")
        f.close()
         
    def load_data(self, data, format="DAT", has_header=True, clear=True, silent=False):
        xydata = []
        max_y = 0.0
    
        if clear:
            self.clear(update=False)    

        if format=="DAT":
            if has_header:
                header, data = data.split("\n", 1)
            for i, line in enumerate(data.split("\n")):
                if line != "": #i is not 0 and 
                    x, y = map(float, line.split())
                    max_y = max(y, max_y)
                    self.xy_data.append(x,y)
        if format=="BIN":
            import struct
            #open file
            f = None
            close = False
            if type(data) is file:
                f = data
            elif type(data) is str:
                f = open(data, 'rb')
                close = True
            else:
                raise TypeError, "Wrong data type supplied for binary format, must be either file or string, but %s was given" % type(data)
            if f != None:
                #seek data limits
                f.seek(214)
                stepx, minx, maxx = struct.unpack("ddd", f.read(24))
                nx = int((maxx-minx)/stepx)
                #read values                          
                f.seek(250)
                n = 0
                while n < nx:
                    y, = struct.unpack("H", f.read(2))
                    max_y = max(y, max_y)
                    self.xy_data.append(minx + stepx*n, float(y))
                    n += 1
                #close file
                if close: f.close()
            
        print max_y
        #import data            
        #if xydata != []:
        #    for x, y in xydata:
        #        self.xy_data.append(x, y / max_y )
        
        self.update_data(silent=silent)
            
    # ------------------------------------------------------------
    #      Methods & Functions
    # ------------------------------------------------------------ 
    @property
    def max_intensity(self):
        if len(self.xy_data._model_data_x) > 1:
            return np.max(self.xy_data._model_data_y)
        else:
            return 0
    
    def update_data(self, silent=False):
        if len(self.xy_data._model_data_x) > 1:
            
            data_x = self.xy_data._model_data_x
            data_y = self.xy_data._model_data_y
            
            offset = self._display_offset
            
            yscale = self.parent.parent.axes_yscale if (self.parent!=None and self.parent.parent != None) else 1            
            if yscale == 0:
                data_y = data_y / self.parent.parent.get_max_intensity()
            elif yscale == 1:
                data_y = data_y / self.max_intensity
            elif yscale == 2:
                offset *= self.parent.parent.get_max_intensity()
            #elif yscale == 3:
            #    data_y = data_y * self.display_scale
            #    offset *= self.parent.parent.get_max_intensity()
            
            trans = transforms.Affine2D().translate(0, offset)
            data = trans.transform(np.array(zip(data_x, data_y)))
            self.line.set_data(np.transpose(data))
            self.line.set_visible(True)
        else:
            self.line.set_data(self.xy_empty_data)
            self.line.set_visible(False)
        if not silent: self.plot_update.emit()
    
    def clear(self, update=True):
        self.xy_data.clear()
        if update: self.update_data()
    
    def on_update_plot(self, figure, axes, pctrl):
        self.update_data(silent=True)
        
        #Add pattern
        lines = axes.get_lines()
        if not self.line in lines:
            axes.add_line(self.line)
        
        def try_or_die(line):
            try: line.remove()
            except: pass            
        
        yscale = self.parent.parent.axes_yscale if (self.parent!=None and self.parent.parent != None) else 1
        yfactor = 1.0
        if yscale == 0:
            yfactor = 1.0 / (self.parent.parent.get_max_intensity() or 1.0)
        elif yscale == 1:
            yfactor = 1.0 / (self.max_intensity or 1.0)
        elif yscale == 2:
            yfactor = 1.0
        
        #Add bg line (if present)
        try_or_die(self.bg_line)
        if self.bg_type == 0 and self._bg_position != 0.0:
            self.bg_line = axes.axhline(y=self.bg_position*yfactor, c="#660099")
        elif self.bg_type == 1 and self.bg_pattern != None:
            bg = ((self.bg_pattern * self.bg_scale) + self.bg_position) * yfactor
            self.bg_line = matplotlib.lines.Line2D(xdata=self.xy_data._model_data_x, ydata=bg, c="#660099")
            axes.add_line(self.bg_line)            
            #print "ADDING BG LINE!!"
        else:
            self.bg_line = None
            
        #Add bg line (if present)
        try_or_die(self.sd_line)
        if self._sd_degree != 0.0:
            self.sd_line = matplotlib.lines.Line2D(xdata=self.xy_data._model_data_x, ydata=self.sd_data, c="#660099")
            axes.add_line(self.sd_line)
        else:
            self.sd_line = None
    
        #Add shifted line (if present)
        try_or_die(self.shifted_line)
        try_or_die(self.reference_line)
        if self._shift_value != 0.0:
            self.shifted_line = matplotlib.lines.Line2D(xdata=(self.xy_data._model_data_x-self._shift_value), ydata=self.xy_data._model_data_y, c="#660099")
            position = self.parent.parent.data_goniometer.get_2t_from_nm(self.shift_position)
            self.reference_line = axes.axvline(x=position, c="#660099", ls="--")     
            axes.add_line(self.shifted_line)
        else:
            self.shifted_line = None
            self.reference_line = None
    
    # ------------------------------------------------------------
    #      Background Removal
    # ------------------------------------------------------------
    def remove_background(self):
        y_data = self.xy_data._model_data_y
        bg = 0
        if self.bg_type == 0:
            bg = self.bg_position
        elif self.bg_type == 1 and self.bg_pattern != None and not (self.bg_position == 0 and self.bg_scale == 0):
            bg = self.bg_pattern * self.bg_scale + self.bg_position
        y_data -= bg
        self.xy_data._model_data_y = y_data - np.min(y_data)
        self.bg_pattern = None
        self.bg_scale = 0.0
        self.bg_position = 0.0
        self.update_data()
        
    def find_bg(self):
        if self.bg_type == 0:
            y_min = np.min(self.xy_data._model_data_y)
            self.bg_position = y_min
        #elif self.bg_type == 1:
        #    self.bg_scale = #TODO
           


    # ------------------------------------------------------------
    #       Data Smoothing
    # ------------------------------------------------------------
    def smooth_data(self):
        y_data = self.xy_data._model_data_y
        if self.sd_degree > 0:
            degree = int(self.sd_degree)
            smoothed = smooth(y_data, degree)
            #smoothed = y_data[:degree] + smoothed + y_data[-degree:]
            self.xy_data._model_data_y = smoothed
        self.sd_degree = 0.0
        self.update_data()            
    
    def try_smooth_data(self):
        y_data = self.xy_data._model_data_y
        if self.sd_degree > 0:
            degree = int(self.sd_degree)
            smoothed = smooth(y_data, degree)
            self.sd_data = smoothed
           
    # ------------------------------------------------------------
    #       Data Shifting
    # ------------------------------------------------------------
    def shift_data(self):
        x_data = self.xy_data._model_data_x
        print self.shift_value
        if self.shift_value != 0.0:
            x_data = x_data - self.shift_value
            self.xy_data._model_data_x = x_data
            for marker in self.parent.data_markers._model_data:
                marker.data_position = marker.data_position-self.shift_value
        self.shift_value = 0.0
        self.update_data()
            
    def find_shift_value(self):
        position = self.parent.parent.data_goniometer.get_2t_from_nm(self.shift_position)
        if position > 0.1:
            x_data = self.xy_data._model_data_x
            y_data = self.xy_data._model_data_y
            max_x = position + 0.5
            min_x = position - 0.5
            condition = (x_data>=min_x) & (x_data<=max_x)
            section_x, section_y = np.extract(condition, x_data), np.extract(condition, y_data)
            actual_position = section_x[np.argmax(section_y)]
            self.shift_value = actual_position - position
            
    pass #end of class

