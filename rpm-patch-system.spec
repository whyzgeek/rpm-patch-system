Name: rpm-patch-system
Summary: rpm-patch-system - Simple patch system.
Version: 1.0.6
Release: 1
Requires: zenoss, patchutils
License: GPLv2
Vendor: whyzgeek
Packager: whyzgeek
Group: Development
BuildRoot: %{_tmppath}/%{name}-%{version}-%(id -u -n)
BuildArch: noarch
Prefix: /usr


# we need to do this so that we don't generate python bytecode for the
# wrong python version
%define __os_install_post \
  /usr/lib/rpm/redhat/brp-compress \
  /usr/lib/rpm/redhat/brp-strip /usr/bin/strip \
  /usr/lib/rpm/redhat/brp-strip-static-archive /usr/bin/strip \
  /usr/lib/rpm/redhat/brp-strip-comment-note /usr/bin/strip /usr/bin/objdump \
  /usr/lib/rpm/redhat/brp-java-repack-jars

%description
Simple patch system.

%prep

%build

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
mkdir -p %{buildroot}/%{prefix}/share/%{name}
mkdir -p %{buildroot}/%{prefix}/share/%{name}/patches

cd %(pwd)/../SOURCES
for i in *.py ; do
  if [ -f "$i" ]; then
    cp "$i" %{buildroot}/%{prefix}/share/%{name}/"$i"
    echo "Copied $i to" %{buildroot}/%{prefix}/share/%{name}/"$i"
    chmod 0755 %{buildroot}/%{prefix}/share/%{name}/"$i"
  fi
done

for i in *.json ; do
  if [ -f "$i" ]; then
    cp "$i" %{buildroot}/%{prefix}/share/%{name}/"$i"
    echo "Copied $i to" %{buildroot}/%{prefix}/share/%{name}/"$i"
  fi
done

# Copying the patches
cp -r patches/* %{buildroot}/%{prefix}/share/%{name}/patches

< /dev/null cat > %{_tmppath}/%{name}-filelist

echo "%{prefix}/share/%{name}" >> %{_tmppath}/%{name}-filelist
( cd %{buildroot} && find ./%{prefix}/share/%{name}/patches -type f -print0 | xargs -0 chmod 0644 )

# In case of upgrade or remove, revert all patches
%pre 
if [ "$1" = "2" ]; then
su - -c "%{prefix}/share/%{name}/apply_patch.py --revert"
fi

%preun 
if [ "$1" = "0" ]; then
su - -c "%{prefix}/share/%{name}/apply_patch.py --revert"
fi

%post
su - -c "%{prefix}/share/%{name}/apply_patch.py --apply"


%clean
rm -rf %{_builddir}/%{name}
rm -rf %{_tmppath}/%{name}-filelist
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%files -f %{_tmppath}/%{name}-filelist
%defattr(-,root,root)
