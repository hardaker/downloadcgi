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
	if ($rule->{'type'} eq 'print') {
	    print $rule->{'expression'},"\n";
	} elsif ($rule->{'type'} eq 'printfile') {
	    print_file($rule->{'expression'});
	} elsif ($rule->{'type'} eq 'list') {
	    next if ($#{$rule->{'files'}} == -1);
	    my @files = @{$rule->{'files'}};

	    # XXX: better sort here
	    if ($rule->{'sortby'} eq 'name') {
		@files = sort @files;
	    } elsif ($rule->{'sortby'} eq 'date') {
		@files = sort sort_by_date @files;
	    } else {
		@files = sort sort_version_before_package @files;
	    }

	    # XXX: allow other rule-defined formats
	    my $format = " <li><a href=\"%s\">%s</a></li>\n";

	    # XXX: allow other rule-defined prefix/postfixes
	    print "<ul>\n";
	    foreach my $file (@files) {
		printf($format, $file, $file);
	    }
	    print "</ul>\n";
	} elsif ($rule->{'type'} eq 'ignore') {
	    # no op
	} else {
	    print STDERR "Download ERROR: unknownrule type $rule->{'type'}\n";
	}
    }
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

Copyright (c) 2010 Wes Hardaker

All rights reserved.  This program is free software; you may
redistribute it and/or modify it under the same terms as Perl itself.

