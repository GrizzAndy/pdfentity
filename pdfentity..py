from PyQt6 import QtWidgets, QtGui, QtCore
import fitz  # PyMuPDF
from PIL import Image
import json
import sys

class PDFAnnotationTool(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Annotation Tool")
        self.setGeometry(100, 100, 1400, 900)  # Slightly larger window for better view

        # Initialize PDF and Annotation Data
        self.pdf_document = None
        self.current_page_index = 0
        self.annotations = []
        self.zoom_level = 1.0
        self.start_x = 0
        self.start_y = 0
        self.rect = None
        self.rectangles = []  # Store drawn rectangles
        self.selected_criteria_index = None

        # Undo/Redo Stacks
        self.undo_stack = []
        self.redo_stack = []

        # UI Setup
        self.setup_ui()

    def setup_ui(self):
        # Central Widget
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        # Layouts
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        toolbar_layout = QtWidgets.QHBoxLayout()
        viewer_layout = QtWidgets.QHBoxLayout()
        sidebar_layout = QtWidgets.QVBoxLayout()

        # Toolbar as Dropdown Menu
        menubar = self.menuBar()
        toolbar_menu = menubar.addMenu("Toolbar")

        # Create a unified action button layout to reduce clutter
        button_configurations = [
            ("Open PDF", self.open_pdf),
            ("New JSON", self.new_json),
            ("Save JSON", self.save_json),
            ("Load JSON", self.load_json),
            ("Export Annotations", self.export_annotations),
            ("Previous Page", self.previous_page),
            ("Next Page", self.next_page),
            ("Zoom In", self.zoom_in),
            ("Zoom Out", self.zoom_out),
            ("Reset Zoom", self.reset_zoom),
            ("Undo", self.undo_action),
            ("Redo", self.redo_action),
        ]

        for text, slot in button_configurations:
            action = QtGui.QAction(text, self)
            action.triggered.connect(slot)
            toolbar_menu.addAction(action)

        # Adding zoom buttons to the toolbar
        zoom_in_btn = QtWidgets.QPushButton("Zoom In (+)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_out_btn = QtWidgets.QPushButton("Zoom Out (-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(zoom_in_btn)
        toolbar_layout.addWidget(zoom_out_btn)
        # Viewer Area
        viewer_layout.setContentsMargins(15, 15, 15, 15)
        self.viewer = QtWidgets.QLabel(self)
        self.viewer.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.viewer.setMouseTracking(True)
        self.viewer.mousePressEvent = self.start_draw_rectangle
        self.viewer.mouseMoveEvent = self.update_rectangle
        self.viewer.mouseReleaseEvent = self.finish_rectangle
        self.viewer.wheelEvent = self.handle_wheel_event  # Add mouse wheel event for zoom in and out
        viewer_scroll_area = QtWidgets.QScrollArea()
        viewer_scroll_area.setWidgetResizable(True)
        viewer_scroll_area.setWidget(self.viewer)
        viewer_scroll_area.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        viewer_layout.addWidget(viewer_scroll_area)

        # Sidebar for Criteria and Entities Management
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(15)

        criteria_group = QtWidgets.QGroupBox("Criteria Management")
        criteria_layout = QtWidgets.QVBoxLayout()
        self.criteria_list = QtWidgets.QListWidget()
        self.criteria_list.itemClicked.connect(self.highlight_criteria)
        self.criteria_list.setStyleSheet("font-size: 14px;")
        criteria_layout.addWidget(self.criteria_list)

        add_criteria_btn = QtWidgets.QPushButton("Add Criteria")
        add_criteria_btn.clicked.connect(self.add_criteria)
        add_criteria_btn.setStyleSheet("font-size: 14px;")
        criteria_layout.addWidget(add_criteria_btn)

        delete_criteria_btn = QtWidgets.QPushButton("Delete Criteria")
        delete_criteria_btn.clicked.connect(self.delete_criteria)
        delete_criteria_btn.setStyleSheet("font-size: 14px;")
        criteria_layout.addWidget(delete_criteria_btn)

        criteria_group.setLayout(criteria_layout)
        criteria_group.setStyleSheet("font-size: 16px;")
        sidebar_layout.addWidget(criteria_group)

        entity_group = QtWidgets.QGroupBox("Entity Management")
        entity_layout = QtWidgets.QVBoxLayout()
        self.entity_list = QtWidgets.QListWidget()
        self.entity_list.setStyleSheet("font-size: 14px;")
        entity_layout.addWidget(self.entity_list)

        add_entity_btn = QtWidgets.QPushButton("Add Entity")
        add_entity_btn.clicked.connect(self.add_entity)
        add_entity_btn.setStyleSheet("font-size: 14px;")
        entity_layout.addWidget(add_entity_btn)

        remove_entity_btn = QtWidgets.QPushButton("Remove Entity")
        remove_entity_btn.clicked.connect(self.remove_entity)
        remove_entity_btn.setStyleSheet("font-size: 14px;")
        entity_layout.addWidget(remove_entity_btn)

        entity_group.setLayout(entity_layout)
        entity_group.setStyleSheet("font-size: 16px;")
        sidebar_layout.addWidget(entity_group)

        # Edit Criteria and Entity
        edit_group = QtWidgets.QGroupBox("Edit Criteria and Entities")
        edit_layout = QtWidgets.QFormLayout()
        self.criteria_name_input = QtWidgets.QLineEdit()
        self.criteria_name_input.setPlaceholderText("Set Criteria Name")
        self.criteria_name_input.returnPressed.connect(self.set_criteria_name)
        self.criteria_name_input.setStyleSheet("font-size: 14px;")
        edit_layout.addRow("Criteria Name:", self.criteria_name_input)

        self.entity_name_input = QtWidgets.QLineEdit()
        self.entity_name_input.setPlaceholderText("Set Entity Name")
        self.entity_name_input.returnPressed.connect(self.set_entity_name)
        self.entity_name_input.setStyleSheet("font-size: 14px;")
        edit_layout.addRow("Entity Name:", self.entity_name_input)

        preview_text_btn = QtWidgets.QPushButton("Preview Text")
        preview_text_btn.clicked.connect(self.preview_text)
        preview_text_btn.setStyleSheet("font-size: 14px;")
        edit_layout.addRow(preview_text_btn)

        edit_group.setLayout(edit_layout)
        edit_group.setStyleSheet("font-size: 16px;")
        sidebar_layout.addWidget(edit_group)

        sidebar_widget = QtWidgets.QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(400)
        viewer_layout.addWidget(sidebar_widget)

        # Combine Layouts
        main_layout.addLayout(viewer_layout)
    def new_json(self):
        self.annotations = []
        self.criteria_list.clear()
        self.entity_list.clear()
        self.selected_criteria_index = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.show_page()

    def open_pdf(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf_document = fitz.open(file_path)
            self.current_page_index = 0
            self.show_page()

    def show_page(self):
        if self.pdf_document is not None:
            page = self.pdf_document.load_page(self.current_page_index)
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            q_image = QtGui.QImage(data, img.width, img.height, QtGui.QImage.Format.Format_RGBA8888)
            pixmap = QtGui.QPixmap.fromImage(q_image)
            self.viewer.setPixmap(pixmap)
            self.viewer.adjustSize()

            # Draw existing rectangles for the selected criteria
            if self.selected_criteria_index is not None:
                criteria = self.annotations[self.selected_criteria_index]
                self.draw_rectangle(criteria['criteria_box'], color=QtCore.Qt.GlobalColor.blue, label=criteria['criteria'])
                for entity in criteria['entities']:
                    self.draw_rectangle(entity['coordinates'], color=QtCore.Qt.GlobalColor.green, label=entity['name'])

            # Ensure a criteria is always selected if available
            if self.annotations and self.selected_criteria_index is None:
                self.selected_criteria_index = 0
                self.criteria_list.setCurrentRow(self.selected_criteria_index)
                self.highlight_criteria(self.criteria_list.item(self.selected_criteria_index))

    def save_json(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save JSON File", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'w') as json_file:
                json.dump(self.annotations, json_file, indent=4)

    def load_json(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load JSON File", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r') as json_file:
                self.annotations = json.load(json_file)
            self.selected_criteria_index = 0 if self.annotations else None
            self.criteria_list.clear()
            for annotation in self.annotations:
                self.criteria_list.addItem(annotation['criteria'])
            self.show_page()

    def export_annotations(self):
        structured_annotations = {
            "entity_sets": [
                {
                    "criteria": annotation["criteria"],
                    "criteria_box": annotation["criteria_box"],
                    "entities": annotation["entities"]
                } for annotation in self.annotations
            ]
        }
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Annotations", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'w') as json_file:
                json.dump(structured_annotations, json_file, indent=4)

    def previous_page(self):
        if self.pdf_document is not None and self.current_page_index > 0:
            self.current_page_index -= 1
            self.show_page()

    def next_page(self):
        if self.pdf_document is not None and self.current_page_index < len(self.pdf_document) - 1:
            self.current_page_index += 1
            self.show_page()

    def zoom_in(self):
        self.zoom_level *= 1.2
        self.show_page()

    def zoom_out(self):
        self.zoom_level /= 1.2
        self.show_page()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.show_page()

    def handle_wheel_event(self, event):
        # Handle zoom with Ctrl + scroll
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
    def start_draw_rectangle(self, event):
        self.start_x = int(event.position().x() / self.zoom_level)
        self.start_y = int(event.position().y() / self.zoom_level)
        self.rect = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Shape.Rectangle, self.viewer)
        self.rect.setGeometry(QtCore.QRect(int(self.start_x * self.zoom_level), int(self.start_y * self.zoom_level), 0, 0))
        self.rect.show()

    def update_rectangle(self, event):
        if self.rect is not None:
            current_x = int(event.position().x() / self.zoom_level)
            current_y = int(event.position().y() / self.zoom_level)
            self.rect.setGeometry(QtCore.QRect(int(self.start_x * self.zoom_level), int(self.start_y * self.zoom_level), int((current_x - self.start_x) * self.zoom_level), int((current_y - self.start_y) * self.zoom_level)))

    def finish_rectangle(self, event):
        if self.rect is not None:
            end_x = int(event.position().x() / self.zoom_level)
            end_y = int(event.position().y() / self.zoom_level)
            new_criteria = {
                "name": f"Entity {len(self.annotations[0]['entities']) + 1 if self.annotations else 1}",
                "coordinates": {
                    "x": self.start_x,
                    "y": self.start_y,
                    "width": end_x - self.start_x,
                    "height": end_y - self.start_y
                }
            }
            if not self.annotations:  # If no criteria exist for the page, add a new one
                annotation = {
                    "criteria": f"Criteria 1",
                    "criteria_box": new_criteria["coordinates"],
                    "entities": []
                }
                self.annotations.append(annotation)
                self.criteria_list.addItem(f"Criteria 1")
                self.selected_criteria_index = 0
                self.update_entity_list()
            else:  # If a criteria already exists, add the rectangle as an entity to the existing criteria
                self.annotations[0]['entities'].append(new_criteria)
            self.rect.hide()
            self.rect = None
            self.show_page()  # Redraw to maintain rectangles
            self.push_undo_stack()

    def draw_rectangle(self, rect_data, color=QtCore.Qt.GlobalColor.red, label=None):
        pixmap = self.viewer.pixmap()
        if pixmap is None:
            return
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(int(rect_data["x"] * self.zoom_level), int(rect_data["y"] * self.zoom_level), int(rect_data["width"] * self.zoom_level), int(rect_data["height"] * self.zoom_level))
        if label:
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black))
            painter.setFont(QtGui.QFont("Arial", 10))
            painter.drawText(int(rect_data["x"] * self.zoom_level), int((rect_data["y"] * self.zoom_level) - 5), label)
        painter.end()
        self.viewer.setPixmap(pixmap)
        self.viewer.update()

    def add_criteria(self):
        criteria_name = self.criteria_name_input.text() or f"Criteria {len(self.annotations) + 1}"
        new_criteria = {
            "criteria": criteria_name,
            "criteria_box": {
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 100
            },
            "entities": []
        }
        self.annotations.append(new_criteria)
        self.criteria_list.addItem(new_criteria['criteria'])
        self.criteria_name_input.clear()
        self.selected_criteria_index = len(self.annotations) - 1
        self.criteria_list.setCurrentRow(self.selected_criteria_index)
        self.update_entity_list(self.annotations[self.selected_criteria_index])
        self.show_page()
        self.push_undo_stack()
    def add_entity(self):
        selected_items = self.criteria_list.selectedItems()
        if selected_items:
            index = self.criteria_list.row(selected_items[0])
            criteria = self.annotations[index]
            entity_name = self.entity_name_input.text() or f"Entity {len(criteria['entities']) + 1}"
            new_entity = {
                "name": entity_name,
                "coordinates": {
                    "x": 150,
                    "y": 150,
                    "width": 100,
                    "height": 100
                }
            }
            criteria['entities'].append(new_entity)
            self.entity_list.addItem(new_entity['name'])
            self.entity_name_input.clear()
            self.update_entity_list(criteria)
            self.show_page()
            self.push_undo_stack()

    def remove_entity(self):
        selected_items = self.entity_list.selectedItems()
        criteria_items = self.criteria_list.selectedItems()
        if selected_items and criteria_items:
            entity_index = self.entity_list.row(selected_items[0])
            criteria_index = self.criteria_list.row(criteria_items[0])
            del self.annotations[criteria_index]['entities'][entity_index]
            self.update_entity_list(self.annotations[criteria_index])
            self.show_page()
            self.push_undo_stack()

    def delete_criteria(self):
        selected_items = self.criteria_list.selectedItems()
        if selected_items:
            for item in selected_items:
                index = self.criteria_list.row(item)
                del self.annotations[index]
                self.criteria_list.takeItem(index)
            self.selected_criteria_index = 0 if self.annotations else None
            self.update_entity_list()
            self.show_page()  # Update to remove deleted rectangles
            self.push_undo_stack()

    def highlight_criteria(self, item):
        index = self.criteria_list.row(item)
        self.selected_criteria_index = index
        criteria = self.annotations[index]
        rect_data = criteria["criteria_box"]
        self.draw_highlighted_rectangle(rect_data)
        # Highlight entities within the criteria
        for entity in criteria['entities']:
            self.draw_highlighted_rectangle(entity['coordinates'], color=QtCore.Qt.GlobalColor.green)
        self.update_entity_list(criteria)

    def draw_highlighted_rectangle(self, rect_data, color=QtCore.Qt.GlobalColor.blue):
        pixmap = self.viewer.pixmap()
        if pixmap is None:
            return
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(color, 2, QtCore.Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.drawRect(int(rect_data["x"] * self.zoom_level), int(rect_data["y"] * self.zoom_level), int(rect_data["width"] * self.zoom_level), int(rect_data["height"] * self.zoom_level))
        painter.end()
        self.viewer.setPixmap(pixmap)
        self.viewer.update()

    def update_entity_list(self, criteria=None):
        self.entity_list.clear()
        if criteria:
            for entity in criteria['entities']:
                self.entity_list.addItem(entity['name'])

    def set_criteria_name(self):
        selected_items = self.criteria_list.selectedItems()
        if selected_items:
            index = self.criteria_list.row(selected_items[0])
            self.annotations[index]['criteria'] = self.criteria_name_input.text()
            self.criteria_list.item(index).setText(self.criteria_name_input.text())
            self.criteria_name_input.clear()
            self.show_page()
            self.push_undo_stack()

    def set_entity_name(self):
        selected_items = self.entity_list.selectedItems()
        criteria_items = self.criteria_list.selectedItems()
        if selected_items and criteria_items:
            entity_index = self.entity_list.row(selected_items[0])
            criteria_index = self.criteria_list.row(criteria_items[0])
            self.annotations[criteria_index]['entities'][entity_index]['name'] = self.entity_name_input.text()
            self.entity_list.item(entity_index).setText(self.entity_name_input.text())
            self.entity_name_input.clear()
            self.show_page()
            self.push_undo_stack()
    def preview_text(self):
        selected_items = self.entity_list.selectedItems()
        criteria_items = self.criteria_list.selectedItems()
        if selected_items and criteria_items and self.pdf_document:
            entity_index = self.entity_list.row(selected_items[0])
            criteria_index = self.criteria_list.row(criteria_items[0])
            entity = self.annotations[criteria_index]['entities'][entity_index]

            # Get the current page
            page = self.pdf_document.load_page(self.current_page_index)

            # Extract text within the rectangle (using 300 DPI)
            x = entity['coordinates']['x']
            y = entity['coordinates']['y']
            width = entity['coordinates']['width']
            height = entity['coordinates']['height']
            rect = fitz.Rect(x, y, x + width, y + height)

            # Extract text from the defined area
            extracted_text = page.get_text("text", clip=rect)

            # Show the extracted text in a message box
            QtWidgets.QMessageBox.information(self, "Extracted Text", extracted_text if extracted_text else "No text found in the selected area.")

    def push_undo_stack(self):
        # Make a deep copy of annotations to push to the undo stack
        self.undo_stack.append(json.loads(json.dumps(self.annotations)))
        self.redo_stack.clear()  # Clear the redo stack after a new action

    def undo_action(self):
        if self.undo_stack:
            self.redo_stack.append(json.loads(json.dumps(self.annotations)))  # Save current state to redo stack
            self.annotations = self.undo_stack.pop()  # Restore the last saved state
            self.refresh_ui()

    def redo_action(self):
        if self.redo_stack:
            self.undo_stack.append(json.loads(json.dumps(self.annotations)))  # Save current state to undo stack
            self.annotations = self.redo_stack.pop()  # Restore the state
            self.refresh_ui()

    def refresh_ui(self):
        # Update UI elements with the new state of annotations
        self.criteria_list.clear()
        for annotation in self.annotations:
            self.criteria_list.addItem(annotation['criteria'])
        if self.selected_criteria_index is not None and self.selected_criteria_index < len(self.annotations):
            self.criteria_list.setCurrentRow(self.selected_criteria_index)
        self.update_entity_list(self.annotations[self.selected_criteria_index] if self.selected_criteria_index is not None else None)
        self.show_page()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = PDFAnnotationTool()
    window.show()
    sys.exit(app.exec())
