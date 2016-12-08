# -*- coding: utf-8 -*-

import os

from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSlot, QSettings, QAbstractItemModel, QModelIndex
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog

from gml_application_schema_toolbox import name as plugin_name

from processing.tools.postgis import GeoDB


WIDGET, BASE = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '..', 'ui', 'database_widget.ui'))


class PgsqlConnectionsModel(QAbstractItemModel):

    def __init__(self, parent=None):
        super(PgsqlConnectionsModel, self).__init__(parent)

        self._settings = QSettings()
        self._settings.beginGroup('/PostgreSQL/connections/')

    def _groups(self):
        return self._settings.childGroups()

    def parent(self, index):
        return QModelIndex()

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def rowCount(self, parent):
        return len(self._groups())

    def columnCount(self, parent):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        return self._groups()[index.row()]


class DatabaseWidget(BASE, WIDGET):


    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)
        self.setupUi(self)

        self._accept_mode = QFileDialog.AcceptOpen
        self._pgsql_db = None

        self.pgsqlFormWidget.setVisible(False)
        self.pgsqlConnectionsBox.setModel(PgsqlConnectionsModel())
        self.pgsqlConnectionsRefreshButton.setIcon(
            QgsApplication.getThemeIcon('/mActionRefresh.png'))

    def set_accept_mode(self, accept_mode):
        """QFileDialog.AcceptOpen or QFileDialog.AcceptSave"""
        self._accept_mode = accept_mode

    @pyqtSlot(bool)
    def on_sqliteRadioButton_toggled(self, checked):
        print('on_sqliteRadioButton_toggled')
        self.sqliteFormWidget.setVisible(self.sqliteRadioButton.isChecked())

    @pyqtSlot(bool)
    def on_pgsqlRadioButton_toggled(self, checked):
        print('on_pgsqlRadioButton_toggled')
        self.pgsqlFormWidget.setVisible(self.pgsqlRadioButton.isChecked())

    @pyqtSlot()
    def on_sqlitePathButton_clicked(self):
        current_path = self.sqlitePathLineEdit.text()
        filter = self.tr("SQLite Files (*.sqlite)")
        if self._accept_mode == QFileDialog.AcceptOpen:
            path, filter = QFileDialog.getOpenFileName(self,
                self.tr("Open SQLite database"),
                current_path,
                filter)
        else:
            path, filter = QFileDialog.getSaveFileName(self,
                self.tr("Save to SQLite database"),
                current_path,
                filter)
            if path:
                if os.path.splitext(path)[1] == '':
                    path = '{}.sqlite'.format(path)
        self.sqlitePathLineEdit.setText(path)

    @pyqtSlot(str)
    def on_pgsqlConnectionsBox_currentIndexChanged(self, text):
        if self.pgsqlConnectionsBox.currentIndex() == -1:
            self._pgsql_db = None
        else:
            self._pgsql_db = GeoDB.from_name(self.pgsqlConnectionsBox.currentText())

        self.pgsqlSchemaBox.clear()
        schemas = sorted([schema[1] for schema in self._pgsql_db.list_schemas()])
        for schema in schemas:
            self.pgsqlSchemaBox.addItem(schema)

    @pyqtSlot()
    def on_pgsqlConnectionsRefreshButton_clicked(self):
        self.pgsqlConnectionsBox.setModel(PgsqlConnectionsModel())

    def format(self):
        if self.sqliteRadioButton.isChecked():
            return 'SQLite'
        if self.pgsqlRadioButton.isChecked():
            return "PostgreSQL"

    def datasource_name(self):
        if self.sqliteRadioButton.isChecked():
            path = self.sqlitePathLineEdit.text()
            if path == '':
                QMessageBox.warning(self,
                                    plugin_name(),
                                    "You must select a SQLite file")
                return None
            return path
        if self.pgsqlRadioButton.isChecked():
            if self._pgsql_db is None:
                QMessageBox.warning(self,
                                    plugin_name(),
                                    "You must select a PostgreSQL connection")
                return None
            return 'PG:{}'.format(self._pgsql_db.uri.connectionInfo(True))

    def schema(self, create=False):
        schema = self.pgsqlSchemaBox.currentText()
        if not create:
            return schema
        #if self.pgsqlSchemaBox.currentIndex() == -1:
        schemas = [schema[1] for schema in self._pgsql_db.list_schemas()]
        if not schema in schemas:
            res = QMessageBox.question(self,
                                       plugin_name(),
                                       self.tr('Create schema "{}" ?').
                                       format(schema))
            if res != QMessageBox.Ok:
                return False
            self._pgsql_db.create_schema(schema)
        return schema

