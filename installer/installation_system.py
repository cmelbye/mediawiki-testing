# This software, copyright (C) 2008-2009 by Wikiation. 
# This software is developed by Kim Bruning.
#
# Distributed under the terms of the MIT license.

import settings_handler as settings
import os, os.path, shutil
import subprocess
from tags import Tags


class Installer_Exception(Exception):
	pass

class Installation_System(object):
	"""An Abstract Installation System. Don't instantiate this class directly.
		An installation system understands how to install and uninstall
		'things' (instances). An instance might be a particular wiki
		(in the case of the mediawiki installer) or a particular extension 
		in that wiki (extension installer), or perhaps a tool from the wikiation
		toolkit. 
		Next to installing and uninstalling, an installer can also determine
		the status of an instance (installed or uninstalled), and can provide
		lists of instances that are available or installed"""
	system_name=None
	destination_dir=None

	def __init__(self,instance=None):
		self.subsystemdir=os.path.join(settings.installfiles, self.system_name)
		self.destination_dir=None
		self.instance=None
		self.as_alias=None
		self.revision=None
		self.tag=None
		if instance:
			self.set_instance(instance)

	def set_instance(self,instance):
		self.instance=instance	

	def get_installers(self):
		"""list the installers capable of installing an instance"""
		installers=os.listdir(self.subsystemdir)
		installers2=[]
		for line in installers:
			if line.endswith(".install"):
				installers2.append(line.replace(".install",""))

		installers2.sort()
		return installers2

	# XXX This should be a mixin
	def get_revisions(self,installer_name):
		"""list the revisions a particular installer can install"""

		if not installer_name:
			raise Installer_Exception("What installer would you like to know the available revisions for?")

		if not self.exists(installer_name):
                        raise Installer_Exception("Can't find installer "+installer_name)

		return self._get_revisions(installer_name)

	# XXX this should be a mixin
	def _get_revisions(self, installer_name):
		"""actually perform the task of getting revisions for get_revisions
		First checks to see if someone has provided a script to determine
		revisions. If not, falls back to internal method _get_revisions_generic."""
		if self.can_exec(installer_name,'get_revisions'):
			revisions_string=self.exec_task(installer_name,'get_revisions')
			return revisions_string.split('\n')
		else:
			return self._get_revisions_generic(installer_name)

		return None

	# XXX should be a mixin
	def get_tags(self, installer_name):
		"""get list of tags available for this installer."""
		if not installer_name:
			raise Installer_Exception("What extension would you like to know the available revisions for?")

		return Tags().gettags(installer_name)
		

	def get_svnbase(self):
		return None

	def _get_revisions_generic(self, installer):
		"""directly query svn to get a list of available revisions. Usually this is adequate."""

		loglist=self._get_revisions_generic_raw(installer)
		if loglist:
			revs=[]
			for line in loglist:
				if line.startswith("r"):
					rev=line.split()[0]	#get the first value
					revs.append(rev[1:])		# strip off the leading r

			return revs

		return None	# just to make explicit what happens otherwise.

	def _get_revisions_generic_raw(self, installer):
		"""do the actual svn query"""
		svnbase=self.get_svnbase()
		if svnbase:
			location=svnbase+"/"+installer
			loglist=list(os.popen('svn log --quiet '+location))
			# example excerpt of data generated by the above line
			# ------------------------------------------------------------------------
			# r47364 | kim | 2009-02-17 17:13:44 +0100 (Tue, 17 Feb 2009)
			# ------------------------------------------------------------------------
			# r47348 | kim | 2009-02-17 00:40:59 +0100 (Tue, 17 Feb 2009)
			# ------------------------------------------------------------------------
			# r47345 | kim | 2009-02-17 00:29:07 +0100 (Tue, 17 Feb 2009)
			# |-----| 
			# we need the numbers after the first r on the line
			return loglist


	def exists(self,installer_name):
		"""checks to see if a particular installer exists"""
		return installer_name in self.get_installers()

	def installdir_name(self, installer_name):
		"""returns the location of the .install directory for the given installer_name.
		An installer directory is where we store all the scripts to install one particular
		extension, tool from the wikiation_toolkit, or etc. """
		return os.path.join(self.subsystemdir, installer_name+".install")
	

	def exec_task(self, installer_name, task, env=None):
		"""attempt to execute a file starting with the name of task[o] (ie. task.sh, task.py, task.pl, etc)
		   * We look for the files in the relevant .install directoty (see also: installdir_name() )
		   * task is name of some task. If task requires args, provide a list, task[0] is name of task, task[1:] is args
		   * if no such file exists or file fails to run, return an exception.
		   * if more than one match exists, one match is picked
		        Exactly Which match is picked is not defined
			(so Don't Do That)
			* Quite some information is passed via environment vars. Set debug=True in settings.py to take a look.
			returns 
			* stdout returned by task command if successful
			* None if task not available
			
			raises  exception if problems occur
			"""
		
		installdir=self.installdir_name(installer_name)

		if env==None:
			env={}

		env=dict(env)

		env["INSTALL_DIR"]=installdir
		env["DESTINATION_DIR"]=self.destination_dir
		env["NAME"]=installer_name
		env["REVISION"]=self.revision or ''
		env["TAG"]=self.tag or ''
		env["MYSQL_COMMAND"]=settings.mysql_command

		if isinstance(task,str):
			task2=[task]
		else:
			task2=list(task)

		dirlist=os.listdir(installdir)
		for filename in dirlist:
			if filename.startswith(task2[0]):
				task2[0]=os.path.join(installdir,filename)
				try:
					if settings.debug:
						print " === " +task+" === "
						print "environment",env
						print "task",task2

					process=subprocess.Popen(task2 ,stdout=subprocess.PIPE, env=env)
					stdout,stderr=process.communicate()

					if settings.debug:
						print "stdout:",stdout
						print "stderr:",stderr
						print

				except Exception, e:
					#reraise with task and env info included, to give us a clue where we went wrong
					raise Exception((e,task2,env))
				return stdout
		return None

	def can_exec(self, installer_name, task):
		"""checks to see if there is an executable script available for the given task
		It's usually a good idea to call this before running exec_task
		
		returns: True if script exists"""
		installdir=self.installdir_name(installer_name)
		dirlist=os.listdir(installdir)
		for filename in dirlist:
			if filename.startswith(task) and os.access(os.path.join(installdir,filename), os.X_OK):
				return True
		
		return False
	
	
	def get_installed(self):
		"""return a list of installed items"""
		installed=[]
		for installer_name in self.get_installers():
			if self.is_installed(installer_name):
				installed.append(installer_name)

		return installed
	
	def is_installed(self,installer_name):
		"""return true if the particular item is already installed"""
		if not self.destination_dir:
			raise Installer_Exception("Installation_system: Internal Error: No destination_dir provided")

		if self.can_exec(installer_name,"is_installed"):
			rv=self.exec_task(installer_name,"is_installed")
			if rv==None:
				print "Warning: "+installer_name+" does not support 'is_installed'."
			elif "true" in rv:
				return True
			elif "false" in rv:
				return False
			else:
				print "Warning: "+installer_name+" 'is_installed' provides unexpected output "
		else:
			print "Warning: "+installer_name+" has some problems with 'is_installed'."

		return None


	def get_info(self,installer_name):
		"""print out information about the target from the info file"""
		info_filename=os.path.join(self.installdir_name(installer_name),"info")
		if not self.exists(installer_name):
			raise Installer_Exception("Can't find installer "+installer_name)

		if os.path.exists(info_filename):
			print file(info_filename).read()
			return True
		else:
			print "This installer provides no information."

	def install (self, installer_name):
		"""Actually install the item
			returns True if installation successful, false if not, and None if unknown"""
		if not self.exists(installer_name):
			raise Installer_Exception("Can't find installer "+installer_name)

		if self.is_installed(installer_name):
			print installer_name,"already installed."
			return
		try:
			self.download(installer_name)
			self.install_settings(installer_name)
			self.setup(installer_name)
		# ...
		except Installer_Exception:
			pass
		except:
			raise

		#query the installer to see if ot thinks the component is properly installed
		# any flaws at this point are the fault of the installer :-P
		return self.is_installed(installer_name)
	
	def setup(self, installer_name, destination_dir=None):
		"""perform actions needed to setup an extension post-download"""

		destination_dir=destination_dir or self.destination_dir
		if not destination_dir:
			raise Exception("Installation_system: Internal Error: No  destination_dir provided")

		if not self.exists(installer_name):
			raise Installer_Exception("Can't find installer "+installer_name)

		self._setup(installer_name,destination_dir)

	def _setup(self, installer_name, destination_dir):
		"""actually perform the setup required by setup (do not call directly)"""
		#silently fail if there's no setup script
		if not self.can_exec(installer_name,"setup"):
			return 

		self.exec_task(installer_name,"setup")

	def download (self, installer_name, destination_dir=None):
		"""perform actions needed to download all the files we need"""

		destination_dir=destination_dir or self.destination_dir
		if not destination_dir:
			raise Exception("Installation_system: Internal Error: No  destination_dir provided")

		if not self.exists(installer_name):
			raise Installer_Exception("Can't find installer "+installer_name)

		self._download(installer_name, destination_dir)

	def _download(self, installer_name, destination_dir):
		"""actually perform the download for download() (do not call directly)"""
		# if a particular step in the install procedure is not provided
		# we simply skip it
		if not self.can_exec(installer_name,"download"):
			print "notice: cannot execute download script for "+installer_name
			return

		self.exec_task(installer_name,"download")

	def install_settings(self,installer_name):
		"""do setup for settings files, etc... override to do something useful"""
		pass

	def uninstall_settings(self,installer_name):
		"""remove settings files etc... override to do something useful"""
		pass

	def uninstall (self, installer_name, destination_dir=None):
		"""uninstall the component"""

		destination_dir=destination_dir or self.destination_dir
		if not destination_dir:
			raise Installer_Exception("Installation_system: Internal Error: No  destination_dir provided")

		if not self.exists(installer_name):
			raise Installer_Exception("Can't find installer "+str(installer_name))
			
		if not self.is_installed(installer_name):
			print installer_name+" does not appear to be installed"
			return

	
		self._uninstall(installer_name, destination_dir)

		self.uninstall_settings(installer_name)
		# use is_installed to determine success.
		return not self.is_installed(installer_name) 
		
	def _uninstall(self,installer_name, destination_dir):
		"""actually uninstall the component (do not call directly)"""
		# if a particular step in the install procedure is not provided
		# we simply skip it
		if self.can_exec(installer_name,"uninstall"):
			self.exec_task(installer_name,"uninstall")
	
	def get_extensionsdir(self):
		"""return the relevant extensionsdir to look in"""
		extensionsdir=None
		if self.tag:
			extensionsdir=settings.tagsdir+"/"+self.tag+"/"+settings.extensionssubdir
		else:
			extensionsdir=settings.extensionsdir

		return extensionsdir
