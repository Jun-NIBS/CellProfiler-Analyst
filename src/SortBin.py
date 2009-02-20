from DBConnect import DBConnect
from TileCollection import TileCollection
from ImageTile import ImageTile
from ImageTileSizer import ImageTileSizer
from Properties import Properties
import ImageTools
import cPickle
import wx

p  = Properties.getInstance()
db = DBConnect.getInstance()


class SortBinDropTarget(wx.DropTarget):
    def __init__(self, bin):
        self.data = wx.CustomDataObject("ObjectKey")
        wx.DropTarget.__init__(self, self.data)
        self.bin = bin
    
    def OnDrop(self, x, y):
        self.GetData()
        key = self.data.GetData()
        self.bin.ReceiveDrop(key)
        return True


class SortBin(wx.ScrolledWindow):
    '''
    SortBins contain collections of objects as small image tiles
    that can be dragged to other SortBins for classification.
    '''
    def __init__(self, parent, chMap=None, label='', classifier=None):
        wx.ScrolledWindow.__init__(self, parent)
        self.SetDropTarget(SortBinDropTarget(self))
        
        self.label = label
        self.tiles = []
        if chMap:
            self.chMap = chMap
        else:
            self.chMap = p.image_channel_colors
        self.classifier = classifier
        self.TC = None
        
        self.SetBackgroundColour('#000000')
        self.sizer = ImageTileSizer()
        self.SetSizer(self.sizer)

        (w,h) = self.sizer.GetSize()
        self.SetScrollbars(20,20,w/20,h/20,0,0)
        self.EnableScrolling(x_scrolling=False, y_scrolling=True)
                
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        
        self.CreatePopupMenu()
        
    
    def __str__(self):
        return 'Bin %s with %d objects'%(self.label, len(self.sizer.GetChildren()))
    
        
    def CreatePopupMenu(self):
        popupMenuItems = ['View full images of selected',
                          'Select all - [ctrl+a]',
                          'Deselect all - [ctrl+d]',
                          'Remove selected - [Delete]',
                          'Rename class',
                          'Delete bin']
        self.popupItemIndexById = {}
        self.popupMenu = wx.Menu()
        for i, item in enumerate(popupMenuItems):
            id = wx.NewId()
            self.popupItemIndexById[id] = i
            self.popupMenu.Append(id,item)
        self.popupMenu.Bind(wx.EVT_MENU,self.OnSelectFromPopupMenu)
            
        
    def OnKey(self, evt):
        ''' Keyboard shortcuts '''
        if evt.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_BACK]:        # delete
            self.DestroySelectedTiles()
            self.SetVirtualSize(self.sizer.CalcMin())
        elif evt.ControlDown() or evt.CmdDown():
            if evt.GetKeyCode() == ord('A'):
                self.SelectAll()
            elif evt.GetKeyCode() == ord('D'):
                self.DeselectAll()
            elif evt.GetKeyCode() == ord('I'):
                [t.ToggleSelect() for t in self.tiles]
            else:
                evt.Skip()
        else:
            evt.Skip()
            
    def OnRightDown(self, evt):
        ''' On right click show popup menu. '''
        self.PopupMenu(self.popupMenu, evt.GetPosition())
        
    
    def OnSelectFromPopupMenu(self, evt):
        ''' Handles selections from the popup menu. '''
        choice = self.popupItemIndexById[evt.GetId()]
        if choice == 0:
            for key in self.SelectedKeys():
                imViewer = ImageTools.ShowImage((key[0],key[1]), self.chMap[:], parent=self.classifier,
                                        brightness=self.classifier.brightness, scale=self.classifier.scale)
                pos = db.GetObjectCoords(key)
                imViewer.imagePanel.SelectPoints([pos])
        elif choice == 1:
            self.SelectAll()
        elif choice == 2:
            self.DeselectAll()
        elif choice == 3:
            self.DestroySelectedTiles()
        elif choice == 4:
            self.classifier.RenameClass(self.label)
        elif choice == 5:
            self.classifier.RemoveSortClass(self.label)
    
    
    def AddObject(self, obKey, chMap, priority=1, pos='first'):
        if self.TC == None:
            self.TC = TileCollection.getInstance()
        imgs = self.TC.GetTileData(obKey, self.classifier, priority=priority)
        newTile = ImageTile(self, obKey, imgs, chMap, False, scale=self.classifier.scale, 
                            brightness=self.classifier.brightness)
        self.tiles.append(newTile)
        if pos == 'first':
            self.sizer.Insert(0, newTile, 0, wx.ALL|wx.EXPAND, 1 )
        else:
            self.sizer.Add(newTile, 0, wx.ALL|wx.EXPAND, 1)
        self.SetVirtualSize(self.sizer.CalcMin())
        return newTile
                 
                        
    def AddObjects(self, obKeys, chMap, priority=1, pos='first'):
        if self.TC == None:
            self.TC = TileCollection.getInstance()
        imgSet = self.TC.GetTiles(obKeys, self.classifier, priority=priority)
        for obKey, imgs in zip(obKeys, imgSet):
            newTile = ImageTile(self, obKey, imgs, chMap, False, scale=self.classifier.scale, 
                                brightness=self.classifier.brightness)
            self.tiles.append(newTile)
            if pos == 'first':
                self.sizer.Insert(0, newTile, 0, wx.ALL|wx.EXPAND, 1 )
            else:
                self.sizer.Add(newTile, 0, wx.ALL|wx.EXPAND, 1)
        self.SetVirtualSize(self.sizer.CalcMin())
        self.classifier.UpdateBinLabels()

    
    def RemoveKey(self, obKey):
        ''' Removes the specified tile. '''
        for t in self.tiles:
            if t.obKey == obKey:
                self.tiles.remove(t)
                self.sizer.Remove(t)
        self.SetVirtualSize(self.sizer.CalcMin())


    def DestroySelectedTiles(self):
        for obKey, tile in zip(self.SelectedKeys(), self.Selection()):
#            self.classifier.tiles.pop(obKey)
            self.tiles.remove(tile)
            self.sizer.Remove(tile)
            tile.Destroy()
        self.Refresh()
        self.Layout()
        self.classifier.UpdateBinLabels()
    
    
    def Clear(self):
        self.SelectAll()
        self.DestroySelectedTiles()         
        self.Refresh()
        self.Layout()

    def find_selected_tile_for_key(self, obkey):
        for t in self.tiles:
            if t.obKey == obkey and t.selected:
                return t
        
    def ReceiveDrop(self, obKeys):
        obKeys = cPickle.loads(obKeys)
        self.DeselectAll()
        for obKey in obKeys:
            tile = self.AddObject(obKey, self.classifier.chMap)
            tile.Select()
        self.SetFocusIgnoringChildren() # prevent children from getting focus (want bin to catch key events)
        
        
    def MapChannels(self, chMap):
        ''' Recalculates the displayed bitmap for all tiles in this bin. '''
        self.chMap = chMap
        for tile in self.tiles:
            tile.MapChannels(self.chMap)
            
    
    def SelectedKeys(self):
        ''' Returns the keys of currently selected tiles on this bin. '''
        return [tile.obKey for tile in self.tiles if tile.selected]
    
    def Selection(self):
        ''' Returns the currently selected tiles on this bin. '''
        tiles = []
        for tile in self.tiles:
            if tile.selected:
                tiles.append(tile)
        return tiles
    
    
    def GetObjectKeys(self):
        return [tile.obKey for tile in self.tiles]
        
    
    def GetNumberOfTiles(self):
        return len(self.tiles)
    
    
    def GetNumberOfSelectedTiles(self):
        return len(self.SelectedKeys())
        
    
    def SelectAll(self):
        ''' Selects all tiles on this bin. '''
        for tile in self.tiles:
            tile.Select()
        
    
    def DeselectAll(self):
        ''' Deselects all tiles on this bin. '''
        for tile in self.tiles:
            tile.Deselect()
            

    def OnFocus(self, evt):
        # stop focus events from propagating to the evil
        # wx.ScrollWindow class which otherwise causes scroll jumping.
        pass


    def OnLeftDown(self, evt):
        ''' Deselect all tiles unless shift is held. '''
        self.SetFocusIgnoringChildren() # prevent children from getting focus (want bin to catch key events)
        if not evt.ShiftDown():
            self.DeselectAll()


    def UpdateTile(self, obKey):
        ''' Called when image data is available for a specific tile. '''
        for t in self.tiles:
            if t.obKey == obKey:
                t.UpdateBitmap()