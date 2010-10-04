#!/usr/bin/perl

use IO::File;
use IO::Dir;
use strict;

my $downloaddir = $ENV{'SCRIPT_FILENAME'};
$downloaddir =~ s/(.*)\/(.*)/$1/;
my $orderrules = "$downloaddir/RULES";

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
		@files = sort sort_versions @files;
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
	next if ($dir eq 'RULES');

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

