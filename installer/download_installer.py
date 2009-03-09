# This software, copyright (C) 2008-2009 by Wikiation. 
# This software is developed by Kim Bruning.
#
# Distributed under the terms of the MIT license.

import settings_handler as settings
import os, os.path, shutil
import subprocess

from installation_system import Installation_System, Installer_Exception
from extension_installer import Extension_Installer_Exception

class Download_Installer_Exception(Extension_Installer_Exception):
	pass

class Unsupported_Exception(Exception):
	pass

class Download_Installer(Installation_System):
	"""download an extension, do nothing else"""
	system_name='download'
	destination_dir=None

	def set_instance(self,instance):
		self.destination_dir=os.path.join(settings.instancesdir,instance,"extensions")
		Installation_System.set_instance(self,instance)

	def get_installers(self):
		l=list(os.popen('svn ls '+settings.extensionsdir))
		# tidy l in place
		for i in range(len(l)):
			l[i]=l[i].strip()
			if l[i].endswith("/"):
				l[i]=l[i][:-1]
		return l
	#exists()  ok.
	
	def installdir_name():
		raise Unsupported_Exception("download installer does not use installdirs")

	def exec_task():
		raise Unsupported_Exception("download installer does not use installdirs, and therefore also does not exec scripts in installdirs")
	
	def can_exec(self, installer_name, task):
		return False	# we don't have an installdir, so we
				# can never exec a task.

	# get_installed: works ok.

	def is_installed(self, installer_name):
		if self.instance==None:
			raise Download_Installer_Exception("no instance specified ... did you try doing   ...  in <instance> ?")
		path=os.path.join(self.destination_dir,installer_name)
		return os.path.isdir(path)

	# get info will cause an exception to be raised
	# install: ok.
	
	def do_download (self, installer_name, destination_dir):
		os.chdir(destination_dir)
		command="svn checkout '"+\
			settings.extensionsdir+"/"+\
			installer_name+"'"
		#print command
		result=os.system(command)
		if result!=0:
			raise Installer_Exception("download failed, return value "+str(result>>8))
	
	def _settings_filepath(self, installer_name):
		settingsdir=os.path.join(self.destination_dir,"../LocalSettings")
		filename=installer_name+".settings.php"
		filepath=os.path.join(settingsdir,filename)
		return filepath

	def do_uninstall(self, installer_name, destination_dir):
		pathname=os.path.join(destination_dir, installer_name)
		shutil.rmtree(pathname,ignore_errors=True)


	def get_svnbase(self):
		return settings.extensionsdir
