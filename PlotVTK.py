# Created by Bastien Rigaud at 24/01/2022
# Bastien Rigaud, PhD
# Laboratoire Traitement du Signal et de l'Image (LTSI), INSERM U1099
# Campus de Beaulieu, Université de Rennes 1
# 35042 Rennes, FRANCE
# bastien.rigaud@univ-rennes1.fr
# Description:

import os
from datetime import datetime
import time
import numpy as np
import vtk
from numpy import poly1d
from vtk.util import numpy_support
from PIL import Image
from PlotScrollNumpyArrays.Plot_Scroll_Images import plot_scroll_Image

def MakeAxesActor(scale, xyzLabels):
    """
    :param scale: Sets the scale and direction of the axes.
    :param xyzLabels: Labels for the axes.
    :return: The axes actor.
    """
    axes = vtk.vtkAxesActor()
    axes.SetScale(scale)
    axes.SetShaftTypeToCylinder()
    axes.SetXAxisLabelText(xyzLabels[0])
    axes.SetYAxisLabelText(xyzLabels[1])
    axes.SetZAxisLabelText(xyzLabels[2])
    axes.SetCylinderRadius(0.5 * axes.GetCylinderRadius())
    axes.SetConeRadius(1.025 * axes.GetConeRadius())
    axes.SetSphereRadius(1.5 * axes.GetSphereRadius())
    tprop = axes.GetXAxisCaptionActor2D().GetCaptionTextProperty()
    tprop.ItalicOn()
    tprop.ShadowOn()
    tprop.SetFontFamilyToTimes()
    # Use the same text properties on the other two axes.
    axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tprop)
    axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tprop)
    return axes


def append_polydata(polydata_list=[]):
    append_filter = vtk.vtkAppendPolyData()
    i = 0
    for poly in polydata_list:
        temp = vtk.vtkPolyData()
        temp.DeepCopy(poly)
        array_names = [temp.GetPointData().GetArrayName(arrayid) for arrayid in
                       range(temp.GetPointData().GetNumberOfArrays())]
        if 'label_color' not in array_names:
            label_color = numpy_support.numpy_to_vtk(i * np.ones(temp.GetNumberOfPoints()))
            label_color.SetName('label_color')
            temp.GetPointData().AddArray(label_color)
            temp.GetPointData().SetActiveScalars('label_color')
        append_filter.AddInputData(temp)
        i += 1
    append_filter.Update()
    return append_filter.GetOutput()


class KeyPressInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent, mapper, actor, corner_annotation, scalar_bar, glyph_actor=None):
        self.parent = parent
        self.mapper = mapper
        self.actor = actor
        self.corner_annotation = corner_annotation
        self.scalar_bar = scalar_bar
        self.glyph_actor = glyph_actor
        self.glyph_opacity = glyph_actor.GetProperty().GetOpacity() if glyph_actor else 0.0
        self.polydata = vtk.vtkPolyData()
        self.polydata.DeepCopy(mapper.GetInput())
        self.warp_filter = vtk.vtkWarpVector()
        self.warp_step = 5
        self.warp_sign = 1
        self.warp_factor = 0
        self.opacity_factor = int(100 * self.actor.GetProperty().GetOpacity())
        self.opacity_sign = 1
        self.opacity_step = 10
        self.array_names = [self.polydata.GetPointData().GetArrayName(arrayid) for arrayid in
                            range(self.polydata.GetPointData().GetNumberOfArrays())] + [None]
        self.index_scalar = 0
        self.update_annotations()
        self.AddObserver("KeyPressEvent", self.key_press_event)

    def update_annotations(self):
        self.corner_annotation.SetText(1,
                                       "Press key:\nT to toggle scalars\nG to toggle glyphs\nD to deform ({:03d}%)\n"
                                       "A for animation\nO for opacity ({:03d}%)\nQ to quit".format(self.warp_factor,
                                                                                                    self.opacity_factor))

    def update_warper(self):
        self.warp_factor = self.warp_factor + self.warp_sign * self.warp_step
        if self.warp_factor == 100 or self.warp_factor == 0:
            self.warp_sign = -1 * self.warp_sign
        self.warp_filter.SetInputData(self.polydata)
        self.warp_filter.SetScaleFactor(self.warp_factor / 100)
        self.warp_filter.Update()
        self.mapper.SetInputData(self.warp_filter.GetOutput())

    def key_press_event(self, obj, event):
        key = self.parent.GetKeySym()
        if key == 'q':
            print(' PlotVTK: closing PlotVTK window')
            self.close_window()
        if key == 't':
            if len(self.array_names) == 0:
                print(' PlotVTK: no scalars found')
                return
            self.index_scalar += 1
            if self.index_scalar == len(self.array_names):
                self.index_scalar = 0
            self.scalar_bar.SetTitle(self.array_names[self.index_scalar])
            if self.array_names[self.index_scalar]:
                self.mapper.ScalarVisibilityOn()
                self.scalar_bar.VisibilityOn()
                self.mapper.GetInput().GetPointData().SetActiveScalars(self.array_names[self.index_scalar])
                self.mapper.SetScalarRange(self.polydata.GetPointData().GetArray(self.index_scalar).GetRange())
            else:
                self.mapper.ScalarVisibilityOff()
                self.scalar_bar.VisibilityOff()
        if key == 'g':
            if not self.glyph_actor:
                print(' PlotVTK: no vectors found')
                return
            current_opacity = self.glyph_actor.GetProperty().GetOpacity()
            self.glyph_actor.GetProperty().SetOpacity(abs(current_opacity - self.glyph_opacity))
        if key == 'd':
            if not self.glyph_actor:
                print(' PlotVTK: no vectors found')
                return
            self.update_warper()
        if key == 'a':
            if not self.glyph_actor:
                print(' PlotVTK: no vectors found for animation')
                return
            root_dir = r'C:\PlotVTK_animations'
            if not os.path.exists(root_dir):
                os.makedirs(root_dir)
            time_var = datetime.now().strftime("%Y%m%d_%H%M%S")
            frame_list = []
            for i in range(40):
                self.update_warper()
                window_to_image_filter = vtk.vtkWindowToImageFilter()
                window_to_image_filter.SetInput(self.parent.GetRenderWindow())
                window_to_image_filter.Update()
                # png_writer = vtk.vtkPNGWriter()
                # png_writer.SetFileName(r'{}_{:03d}.png'.format(time_var, i))
                # png_writer.SetInputData(window_to_image_filter.GetOutput())
                # png_writer.Write()
                image = window_to_image_filter.GetOutput()
                rows, cols, _ = image.GetDimensions()
                sc = image.GetPointData().GetScalars()
                numpy_image = numpy_support.vtk_to_numpy(sc)
                numpy_image = numpy_image.reshape(rows, cols, -1)
                numpy_image = np.flip(numpy_image, 0)
                frame_list.append(Image.fromarray(numpy_image).convert('RGBA', dither=None))
            img, *imgs = frame_list
            img.save(fp=os.path.join(root_dir, r'animation_{}.gif'.format(time_var)), format='GIF', append_images=imgs,
                     save_all=True, duration=len(frame_list)+1, loop=0, quality=100, palettesize=2048)
        if key == 'o':
            self.opacity_factor = self.opacity_factor + self.opacity_sign * self.opacity_step
            if self.opacity_factor == 100 or self.opacity_factor == 0:
                self.opacity_sign = -1 * self.opacity_sign
            self.actor.GetProperty().SetOpacity(self.opacity_factor / 100)
        self.update_annotations()
        render_window = self.parent.GetRenderWindow()
        render_window.Render()
        return

    def close_window(self):
        render_window = self.parent.GetRenderWindow()
        render_window.Finalize()
        self.parent.TerminateApp()
        del render_window, self.parent


def plot_vtk(polydata, secondary=None, opacity=.5):
    '''
    :param polydata: polydata or list of polydata to plot
    :param secondary: secondary polydata or list of polydata for comparison
    :param opacity: opacity of polydata (default: 0.5)
    :return:
    '''

    if isinstance(polydata, list):
        polydata = append_polydata(polydata)

    if isinstance(secondary, list):
        secondary = append_polydata(secondary)

    center_filter = vtk.vtkCenterOfMass()
    center_filter.SetInputData(polydata)
    center_filter.SetUseScalarsAsWeights(False)
    center_filter.Update()
    center = center_filter.GetCenter()
    bounds = polydata.GetBounds()

    # Create camera
    camera = vtk.vtkCamera()
    camera.SetPosition(-5 * (abs(bounds[0] - bounds[1]) / 2), -3 * (abs(bounds[2] - bounds[3]) / 2), 0)
    camera.SetFocalPoint(center[0], center[1], center[2])
    camera.SetViewUp(0, 0, 1)

    colors = vtk.vtkNamedColors()

    # Create the mapper that corresponds the objects of the vtk file
    # into graphics elements
    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputData(polydata)
    mapper.SetScalarRange(polydata.GetScalarRange())

    # Create the Actor
    actor = vtk.vtkActor()
    actor.GetProperty().SetOpacity(opacity)
    actor.SetMapper(mapper)

    if secondary:
        sec_mapper = vtk.vtkDataSetMapper()
        sec_mapper.SetInputData(secondary)
        sec_mapper.SetScalarRange(secondary.GetScalarRange())
        sec_actor = vtk.vtkActor()
        sec_actor.GetProperty().SetOpacity(opacity)
        sec_actor.SetMapper(sec_mapper)

    if polydata.GetPointData().GetVectors():
        # Set up the glyph filter
        glyph = vtk.vtkGlyph3D()
        glyph_mapper = vtk.vtkDataSetMapper()
        glyph_actor = vtk.vtkActor()
        # define glyph filter
        glyph.SetInputData(polydata)
        glyph.SetScaleModeToScaleByVector()
        glyph.SetColorModeToColorByVector()
        glyph.SetRange(polydata.GetPointData().GetVectors().GetRange(-1))
        glyph.OrientOn()
        glyph.Update()
        # define glyph mapper and actor
        glyph_mapper.SetInputConnection(glyph.GetOutputPort())
        # glyph_mapper.SetScalarModeToUsePointFieldData()
        glyph_mapper.SetScalarRange(polydata.GetPointData().GetVectors().GetRange(-1))
        glyph_actor.GetProperty().SetOpacity(0.2)
        glyph_actor.SetMapper(glyph_mapper)
    else:
        glyph_actor = None

    text_property = vtk.vtkTextProperty()
    text_property.SetColor(0, 0, 0)
    text_property.SetFontSize(12)
    text_property.SetItalic(False)
    text_property.SetShadow(False)

    # Scalar bar actor
    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(mapper.GetLookupTable())
    scalar_bar.SetNumberOfLabels(4)
    # scalar_bar.SetBarRatio(0.3)
    # scalar_bar.SetHeight(0.3)
    scalar_bar.SetOrientationToHorizontal()
    scalar_bar.SetHeight(0.1)
    scalar_bar.SetWidth(0.6)
    scalar_bar.SetPosition(0.2, 0.9)
    scalar_bar.SetLabelTextProperty(text_property)
    scalar_bar.SetAnnotationTextProperty(text_property)
    scalar_bar.SetTitleTextProperty(text_property)
    if polydata.GetPointData().GetScalars():
        scalar_bar.SetTitle(polydata.GetPointData().GetScalars().GetName())  # get name of the active scalar
    else:
        scalar_bar.VisibilityOff()

    # Create the Renderer
    renderer = vtk.vtkRenderer()
    renderer.GradientBackgroundOn()
    renderer.SetBackground2(colors.GetColor3d("CadetBlue"))
    renderer.SetBackground(colors.GetColor3d("White"))
    renderer.SetActiveCamera(camera)

    # Create the RendererWindow
    renderer_window = vtk.vtkRenderWindow()
    renderer_window.SetWindowName('PlotVTK')
    renderer_window.AddRenderer(renderer)
    renderer_window.SetSize(800, 800)

    # add corner annotation
    corner_annotation = vtk.vtkCornerAnnotation()
    corner_annotation.SetLinearFontScaleFactor(2)
    corner_annotation.SetNonlinearFontScaleFactor(1)
    corner_annotation.SetMaximumFontSize(20)
    corner_annotation.GetTextProperty().SetColor(colors.GetColor3d("Black"))
    corner_annotation.GetTextProperty().SetJustificationToRight()

    # Create the RendererWindowInteractor and display the vtk_file
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderer_window)
    interactor.SetInteractorStyle(
        KeyPressInteractorStyle(interactor, mapper, actor, corner_annotation, scalar_bar, glyph_actor))

    # Create axes actor
    xyzLabels = ['X', 'Y', 'Z']
    scale = [1.5, -1.5, 1.5]
    axes = MakeAxesActor(scale, xyzLabels)
    om = vtk.vtkOrientationMarkerWidget()
    om.SetOrientationMarker(axes)

    # Position upper left in the viewport.
    om.SetViewport(0, 0, 0.2, 0.2)
    om.SetInteractor(interactor)
    om.EnabledOn()
    om.InteractiveOff()

    # scale actor
    legend_scale_actor = vtk.vtkLegendScaleActor()
    legend_scale_actor.AllAxesOff()
    legend_scale_actor.GetLegendTitleProperty().SetColor(0, 0, 0)
    legend_scale_actor.GetLegendTitleProperty().SetFontSize(10)
    legend_scale_actor.GetLegendTitleProperty().SetItalic(False)
    legend_scale_actor.GetLegendTitleProperty().SetShadow(False)
    legend_scale_actor.GetLegendLabelProperty().SetColor(0, 0, 0)
    legend_scale_actor.GetLegendLabelProperty().SetFontSize(10)
    legend_scale_actor.GetLegendLabelProperty().SetItalic(False)
    legend_scale_actor.GetLegendLabelProperty().SetShadow(False)

    # Add actor to the schene
    renderer.AddActor(actor)
    if secondary:
        renderer.AddActor(sec_actor)
    renderer.AddActor(glyph_actor)
    renderer.AddActor2D(scalar_bar)
    renderer.AddActor(corner_annotation)
    renderer.AddActor(legend_scale_actor)

    # Render and interact
    renderer_window.Render()
    renderer.GetActiveCamera().Zoom(.8)
    renderer_window.Render()

    interactor.Initialize()
    renderer_window.Render()
    interactor.Start()
