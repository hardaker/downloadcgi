#!/usr/bin/perl

use IO::File;
use IO::Dir;
use strict;

my $downloaddir = $ENV{'SCRIPT_FILENAME'};
$downloaddir =~ s/(.*)\/(.*)/$1/;

my $rulesfilename = "RULES";
my $orderrules = "$downloaddir/$rulesfilename";

my %stuff;
my @rules;

my %globalvars;

#
# print http headers
#
print "Content-Type: text/html\n\n";

#
# load the RULES file
#
load_rules();

#
# open the download directory 
#
load_files();

#
# print the results as the final list we've collected
#
print_results();

sub print_results {
    #
    # run through all the rule results and display the output
    #

    foreach my $rule (@rules) {
	my $lastversion;

	if ($rule->{'type'} eq 'print') {
	    print $rule->{'expression'},"\n";
	} elsif ($rule->{'type'} eq 'printfile') {
	    print_file($rule->{'expression'});
	} elsif ($rule->{'type'} eq 'global') {
	    my ($left, $right) = ($rule->{'expression'} =~ (/^(\w+)\s+(.*)/));
	    $globalvars{$left} = $right;
	} elsif ($rule->{'type'} eq 'list') {
	    next if ($#{$rule->{'files'}} == -1);
	    my @files = @{$rule->{'files'}};

	    # XXX: better sort here
	    if (get_param($rule, 'sortby') eq 'name') {
		@files = sort @files;
	    } elsif (get_param($rule, 'sortby') eq 'date') {
		@files = sort sort_by_date @files;
	    } else {
		@files = sort sort_version_before_package @files;
	    }

	    # XXX: allow other rule-defined formats
	    my $format = " <li><a href=\"%s\">%s</a></li>\n";

	    # XXX: allow other rule-defined prefix/postfixes
	    print "<ul>\n";
	    foreach my $file (@files) {
		if (get_param($rule, 'versionspaces') || get_param($rule, 'versionheaders')) {
		    my $version = find_version($file);
		    if (defined($lastversion) && $lastversion ne $version) {
			printf("<br />\n");
		    }
		    if (get_param($rule, 'versionheaders')) {
			if ($lastversion ne $version) {
			    print "</ul>\n" if (defined($lastversion));
			    print "<li>$version</li>\n<ul>\n";
			}
		    }
		    $lastversion = $version;
		}
		printf($format, $file, $file);
	    }
	    print "</ul>\n" if (defined($lastversion));
	    print "</ul>\n";
	} elsif ($rule->{'type'} eq 'ignore') {
	    # no op
	} else {
	    print STDERR "Download ERROR: unknownrule type $rule->{'type'}\n";
	}
    }
}

# find_version() works against at least these:
#   net-snmp-5.4.tar.gz
#   ne-snmp-5.4.3.tar.gz
#   n-f-5.4.3.rc1.tar.gz
#   x-y-aoeu-auoe-5.4.3.pre1.tar.gz
#   x-y-aoeu-auoe-5.4.3.pre1-4.rpm
#   x-y-aoeu-auoe-5.4.3.pre1-4.rpm

sub find_version {
    # fetches the version number out of the first (and only) argument
    my $package = $_[0];

    # strip off "word-" prefixes
    while ($package =~ s/^[a-zA-Z]\w*-//g) { }

    # find the base package version number
    my $version;
    while ($package =~ s/^((\d+|\d+p\d+|rc\d+|pre\d+|fc\d+|i386|ppc)[-\.])//) { $version .= $1; }

    # strip off the potential trailing . or -
    $version =~ s/[-\.]$//;

    return $version;
}

# sorting version numbers by newest first
# XXX: pretty much replaced by the next one; should go away?
sub sort_versions {
    my $aroot = $a;
    my $broot = $b;
    $aroot =~ s/.(pre|rc).*//;
    $broot =~ s/.(pre|rc).*//;
    if ($aroot eq $broot) {
        return 1 if ($a =~ /\.pre/ && $b !~ /pre/); # pre-releases issued first
        return 1 if ($a =~ /\.rc/ && $b !~ /rc/); # then rc releases
    }
    return $broot <=> $aroot if (($broot <=> $aroot) != 0);
    return $broot cmp $aroot;
}

sub sort_version_before_package {
    # figure out the version part of the file name
    my ($aversion) = ($a =~ /-(\d+.*)/);
    my ($bversion) = ($b =~ /-(\d+.*)/);

    $aversion =~ s/.(pre|rc).*//;
    $bversion =~ s/.(pre|rc).*//;

    my $aroot = $aversion;
    my $broot = $bversion;

    $aroot =~ s/\.(pre|rc).*//;
    $broot =~ s/\.(pre|rc).*//;

    if ($aroot eq $broot) {
	# pre-releases issued first
        return 1 if ($aversion =~ /\.pre/ && $bversion !~ /pre/);
	# then rc releases
        return 1 if ($aversion =~ /\.rc/ && $bversion !~ /rc/);
    }
    return $aversion <=> $aversion if (($aversion <=> $aversion) != 0);
    return $broot cmp $aroot;
}

sub sort_by_date {
    return (stat($a))[1] <=> (stat($a))[0];
}

sub match_rule {
    my ($file) = @_;
    foreach my $rule (@rules) {
	if ($file =~ /$rule->{'expression'}/) {
	    push @{$rule->{'files'}}, $file;
	    return;
	}
    }
    print STDERR "Download ERROR: unmatched file in download directory: $file\n";
}

sub load_rules {
    #
    # load the RULES file
    #
    my $fileh = new IO::File $orderrules;
    if (!defined $fileh) {
	Error("Error loading the download list\n");
    }

    while(<$fileh>) {

	# skip comments and blank lines
	next if (/^\s*#/ || /^\s*$/);

	chomp();
	my @ruledata = (/^\s*(\S+)\s+(.*)/);

	if (/^\s+/) {
	    $rules[$#rules]->{$ruledata[0]} = $ruledata[1];
	    next;
	}

	push @rules, { type => $ruledata[0], expression => $ruledata[1] };
    }
    $fileh->close();
}

sub load_files {
    #
    # load the files from the master directory into the rules
    #

    my $dirh = IO::Dir->new($downloaddir);
    if (!defined($dirh)) {
	Error("Error in Generating a Download Listing");
    }

    #
    # loop through the directory contents collecting info
    #

    my $dir;
    while (defined($dir = $dirh->read)) {
	next if ($dir =~ /^\./);
	next if ($dir eq $rulesfilename);

	my $subversion = "&nbsp;";

	match_rule($dir);

	my ($name, $ver, $type) = ($dir =~ /([^\d]+)-([-\.\drcpre]+)\.(.*)/);
	if ($ver =~ s/-([\d\.]+)//) {
	    $subversion = $1;
	}

	if ($type) {
	    $stuff{$ver}{$subversion}{$name}{$type} = [$dir,$subversion];
	}
#    print "<pre>$ver}{$name}{$type = $dir</pre>\n";
    }
}

#
# simply copies a file to stdout
#
sub print_file {
    my ($file) = @_;
    my $fh = new IO::File $file;
    if (!$fh) {
	Error("failed to open a file");
    }
    my $buf;
    while($fh->read($buf, 4096)) {
	print $buf;
    }
}

sub get_param {
    my ($rule, $name) = @_;
    return ($rule->{$name} || $globalvars{$name} || undef);
}

sub Error {
    print "<h2>", $_[0], "</h2>\n";
    print "<p>please contact an administrator</p>\n";
    exit 1;
}

=pod

=head1 NAME

download.cgi -- Organize a download directory

=head1 SYNOPSIS

RULES file example syntax:

  printfile MyHtmlTopStuff.html

  print <h2>tar files:</h2>
  list .*\.tar\.(gz|bz2)

  print <h2>zip files:</h2>
  list .*\.zip

  ignore *~

=head1 INSTALLING

Typically this can be installed by simply copying it to the directory
it should serve and renaming it to I<index.cgi>
(e.g. I</var/www/my-server/download/index.cgi>) .  Make sure to make
it B<executable> and make sure to create a I<RULES> file for it to
read.

You may need to set the I<ExecCGI> option in an apache I<.htaccess>
file as well:

  Options +ExecCGI

=head1 RULES FILE PROCESSING

The script works by first reading in the I<RULES>. file and caching the
results.  Each line is expected to be a comment (prefixed by a #), a
blank line or a configuration token (described in the next section)
followed by argument(s) to the end of the line.

The I<download.cgi> script will then read in the directory in which it
was placed and process each file according to the ordered set of rules
loaded.  The first matching rule will win and the output will be
generated based on that rule.

=head1 CREATING RULES

There are a few different types of syntax lines can go into the I<RULES> file.
Per typical configuration files, lines starting with a # will be
ignore as a comment.

Note: Configuration lines must not start with white-space, as this will be
used to add optional configuration tokens to the rules in the future
and the code already treats white-space starting lines differently.

=head2 Rule Options

Rule options can be created by prefixing a line with a white-space
character.  Thus, the following is a valid single rule definition that
adds the "versionspaces" option to the rule:

    list .*.rpm
    	versionspaces 1

=head2 Rules

=over

=item printfile FILE

The B<printefile> directive takes a single argument and simply dumps that
file out.  It's functionally equivelent to a "include" statement.

=item print TEXT

The B<print> token simply prints the rest of the line to the output page.
It is useful especially for quick header syntax above a I<list>.

=item list REGEXP

This is the real power behind the I<download.cgi> script.  This allows
you to group files in a directory by regular expression matching.  The
list will be printed using HTML <ul> and <li> style tags [future
versions will allow for a more flexible output style].

The list will be sorted by version numbers as best as possible.  The
first number after a - will be considered the start of a version
number and high version numbers will be sorted to higher in the
displayed list (so 1.7.1 will be above 1.7).  The version sorting
algorithm treats I<.preN> and I<.rcN> suffixes differently so that
1.7.1.pre1 will be sorted below 1.7.1.  [future versions will allow
for a more flexible output style].

Note: make sure you realize that a regular expression is required and
typical unix globbing is not supported (yet).  IE, "*.tar.gz" is not a
valid argument.

Extra options:

=over

=item versionspaces 1

This adds a verical space between files of different versions.  This
is most useful for grouping file sets together such as multilpe RPMs
that make up a single version set.

    list mypackage.*.rpm
    	versionspaces 1

=item versionheaders 1

This adds version headers ahead of each section with different
versions so the results look something like:

    + 1.3
      + dnssec-tools-1.3.rpm
      + dnssec-tools-libs-1.3.rpm

    + 1.2
      + dnssec-tools-1.2.rpm
      + dnssec-tools-libs-1.2.rpm

=back

=item global PARAMETER VALUE

This lets you set global parameters that affect all the rules.  For
example, you can have versionspaces turned on for all rules by putting
this at the top of the file:

    global versionspaces 1

=item ignore REGEXP

This allows files to be ignored so that error messages about unknown
files don't get printed to the web server's error log.

=back

=head1 NOTES

This will likely only work with apache as the script expects the
SCRIPT_FILENAME environment variable to be set, which may be an
apache-ism.

=head1 TODO

The following features would be 'nice to haves:' 

- sort by various other methods
- suffix printing (ie, tar.gz, md5, sha, gpg, ...)
- URL prefix other than current
- generic list formatting mechanism 
- hover notes
- caching of data for speed (based on directory modification time)

=head1 AUTHOR

Wes Hardaker E<lt>opensource@hardakers.net<gt>

=head1 COPYRIGHT and LICENSE

Copyright (c) 2010-2011 Wes Hardaker

All rights reserved.  This program is free software; you may
redistribute it and/or modify it under the same terms as Perl itself.

