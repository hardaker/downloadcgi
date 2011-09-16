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
our @names;
my %aliases;

foreach my $i (1..9) {
    $aliases{"h" . $i} = [
	"name %s",
	"  level $i",
        "INHERIT",
	"print <a name=\"goto%s\" />",
	"print <h$i>%s</h$i>",
	];
}

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
    my $currentLevel = 0;

    # Preliminary processing for some rule types to collect some data
    foreach my $rule (@rules) {
	if ($rule->{'type'} eq 'name') {
	    push @names, $rule;
	}
    }

    my @nameList;
    foreach my $rule (@rules) {
	my $lastversion;

	# print STUFF
	if ($rule->{'type'} eq 'print') {
	    print "$rule->{'expression'}","\n";

	# printfile FILENAME
	} elsif ($rule->{'type'} eq 'printfile') {
	    print_file($rule->{'expression'});

	# buttonbar: prints a list of toggle buttons
	} elsif ($rule->{'type'} eq 'buttonbar') {
	    print_button_bar($rule);

        # name SOMETHING
	# names a section (which puts it in a html div wrapper that the
	# buttonbar will create buttons to show/hide it).
	} elsif ($rule->{'type'} eq 'name') {
	    my $strippedName = simplify_name($rule->{'expression'});
	    my $level = get_param($rule, 'level', 1);

	    if ($currentLevel >= $level) {
		print "</div>\n" x ($currentLevel - $level + 1);
	    } elsif ($currentLevel < $level) {
		print "<div>\n" x ($level - $currentLevel - 1 );
	    }

	    print "<div class=\"dcgiDownloadName dcgiLevel$level $strippedName\">\n";
	    push @nameList, "$strippedName";
	    $currentLevel = $level;

	# global THINGY VALUE: Allow global settings that affect all the rules
	} elsif ($rule->{'type'} eq 'global') {
	    my ($left, $right) = ($rule->{'expression'} =~ (/^(\w+)\s+(.*)/));
	    $globalvars{$left} = $right;

        # list REGEXP: list a bunch of files matching a regexp
	} elsif ($rule->{'type'} eq 'list') {
	    next if ($#{$rule->{'files'}} == -1);
	    my @files = @{$rule->{'files'}};

	    my $suffixes = get_param($rule, 'suffixes');
	    my @suffixes;
	    my %newfiles;
	    if ($suffixes) {
		@suffixes = split(/,*\s+/, $suffixes);

		# process the list of suffixes to group them together
		foreach my $file (@files) {
		    my $matches = 0;
		    foreach my $suffix (@suffixes) {
			if ($file =~ /(.*)($suffix)$/) {
			    # matches a known suffix; store the base file name
			    # and the suffix to go with it
			    $newfiles{$1}{$2} = $file;
			    $matches++;
			}
		    }
		    if ($matches == 0) {
			# no suffix matches; take the whole file
			$newfiles{$file}{'__left'} = $file;
		    }
		}

		@files = keys(%newfiles);
	    }

	    # XXX: better sort here
	    if (get_param($rule, 'sortby') eq 'name') {
		@files = sort @files;
	    } elsif (get_param($rule, 'sortby') eq 'date') {
		@files = sort sort_by_date @files;
	    } else {
		@files = sort sort_version_before_package @files;
	    }

	    my $firstItem = 1;
	    my $showdates = get_param($rule, 'showdates', 0);

	    # XXX: allow other rule-defined formats
	    my $format = " <li><a href=\"%s\">%s</a>%s</li>\n";

	    my %donefile; # for catching duplicates

	    # XXX: allow other rule-defined prefix/postfixes
	    print "<ul>\n";
	    foreach my $file (@files) {
		my $prefix = "";
		my $version = find_version($file);

		if (defined($lastversion) && $lastversion ne $version) {
		    if (get_param($rule, 'versionspaces')) {
			$prefix = "<br />\n";
		    }
		    if (get_param($rule, 'versionheaders')) {
			$prefix .= "</ul>\n" if (defined($lastversion));
		    }
		    if ($firstItem) {
			$prefix .= "</ul>";
			$prefix .= "<div ";
			$prefix .= "id=\"$nameList[$#nameList]OlderVersion\" "
			    if ($nameList[$#nameList] ne '');
			$prefix .= "class=\"olderVersions\"><ul>\n";
			$firstItem = 0;
		    }
		    if (get_param($rule, 'versionheaders')) {
			$prefix .= "<li>$version</li>\n<ul>\n";
		    }
		}
		$lastversion = $version;

		if ($suffixes && exists($newfiles{$file})) {
		    my $result = "<li>";
		    my $linkformat = "<a href=\"%s\">%s</a>";
		    my $count = 0;
		    my $firstsuffix;
		    foreach my $suffix (sort keys(%{$newfiles{$file}})) {
			$suffix = "" if ($suffix eq '__left');
			$firstsuffix = $suffix if (!defined($firstsuffix));

			# catch duplicates from bad suffix configs
			next if ($donefile{"$file$suffix"});
			$donefile{"$file$suffix"} = 1;

			if ($count == 0) {
			    print $prefix;
			    $result .=
				"<span class=\"dcgiLinks\"><div class=\"dcgiFirstLink\">" .
				sprintf($linkformat, $newfiles{$file}{$suffix},
					"$file$suffix");

			    if ($showdates || 0) {
				$result .= 
				    get_date_string("$downloaddir/$file$firstsuffix");
			    }

			    $result .= "</div>";

			} else {
			    $result .= "<span class=\"dcgiOtherLinks\">" if ($count == 1);
			    $result .= " <span class=\"dcgiOtherLink\">" . sprintf($linkformat, $newfiles{$file}{$suffix}, "($suffix)") . "</span>";
			}
			$count++;
		    }
		    next if ($count == 0);

		    $result .= "</span>" if ($count => 1); # /dcgiOtherLinks

		    $result .= "</span>"; # /dcgiLinks

		    $result .= "</li>\n";
		    print $result;
		} else {
		    my $dateinfo = "";
		    if ($showdates) {
			$dateinfo = 
			    get_date_string("$downloaddir/$file");
		    }

		    printf($format, $file, $file);
		}
	    }
	    print "</ul>\n";
	    if (! $firstItem) {
		my $name = $nameList[$#nameList];
		print "</div>\n";
		if (defined($name) && $name ne '') {
		    print "<span class=\"dcgiMoreButton\" onClick=\'toggleIt(\"${name}OlderVersion\")' id=\"${name}OlderVersionMoreButton\">more...</span>\n";
		}
	    }
	    if (defined($lastversion) && get_param($rule, 'versionheaders')) {
		print "  </ul>\n" ;
	    }

	# ignore REGEXP: ignores a files matching a particular expression
	} elsif ($rule->{'type'} eq 'ignore') {
	    # no op

        # error: unknown rule type
	} else {
	    print STDERR "Download ERROR: unknownrule type $rule->{'type'}\n";
	}
    }
}

sub get_date_string {
    my ($file) = @_;
    my @dateinfo = localtime((stat("$file"))[9]);
    return sprintf(" <span class=\"dcgiFileDate\">(%04d-%02d-%02d)</spann>",
		   ($dateinfo[5] + 1900),
		   ($dateinfo[4] + 1),
		   ($dateinfo[3]));
}    

# find_version() works against at least these:
#   net-snmp-5.4.tar.gz
#   ne-snmp-5.4.3.tar.gz
#   n-f-5.4.3.rc1.tar.gz
#   x-y-aoeu-auoe-5.4.3.pre1.tar.gz
#   x-y-aoeu-auoe-5.4.3.pre1-4.rpm
#   x-y-aoeu-auoe-5.4.3.pre1-4.rpm
#   dnssec-tools-libs-devel-1.10-1.fc15.x86_64.rpm 

sub find_version {
    # fetches the version number out of the first (and only) argument
    my $package = $_[0];

    # strip off "word-" prefixes
    while ($package =~ s/^[a-zA-Z]\w*-//g) { }

    # find the base package version number
    my $version;
    # matches
    #  	 NUMBER
    #  	 'p'NUMBER
    #  	 'rc'NUMBER
    #  	 'pre'NUMBER
    # (plus a trailing dot or slash)
    while ($package =~ s/^((\d+|\d+p\d+|rc\d+|pre\d+)[-\.])//) {
	$version .= $1;
    }

    if ($package =~ /^\d+$/) {
	# all numbers left
	$version .= $package;
    }

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

    $aversion =~ s/[-.][\D].*//;
    $bversion =~ s/[-.][\D].*//;

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

    my $ret = 0 - compare_parts($aversion, $bversion);
    return $ret if ($ret != 0);
    return 0 - compare_parts($aroot, $broot);
}

sub compare_parts {
    my ($left, $right) = @_;

    my ($leftmaj, $leftrest) = ($left =~ /(\d+)\.(.*)/);
    my ($rightmaj, $rightrest) = ($right =~ /(\d+)\.(.*)/);

    if (!defined($leftmaj) && !defined($rightmaj)) {
	# last digit on both sides
	return $left <=> $right;
    }

    if (!defined($leftmaj) || !defined($rightmaj)) {
	if (defined($leftmaj)) {
	    # is the last on the right greater than the next left digit?
	    if ($right > $leftmaj) {
		return -1;
	    }
	    return 1;
	}

	# is the last on the left greater than the next right digit?
	if ($left > $rightmaj) {
	    return 1;
	}
	return -1;
    }

    if ($leftmaj == $rightmaj) {
	return compare_parts($leftrest, $rightrest);
    }

    return $leftmaj <=> $rightmaj;
}

sub sort_by_date {
    return (stat($a))[1] <=> (stat($a))[0];
}

sub match_rule {
    my ($file) = @_;
    foreach my $rule (@rules) {
	if ($rule->{'type'} eq 'list' && $file =~ /$rule->{'expression'}/) {
	    push @{$rule->{'files'}}, $file;
	    return;
	}
    }
    print STDERR "Download ERROR: unmatched file in download directory: $file\n";
}

sub add_rule_from_line {
    my ($line, $ruleset) = @_;

    my @ruledata = ($line =~ /^\s*(\S+)\s+(.*)/);

    # if the line begins with white-space, it's an extra parameter
    if ($line =~ /^\s+/) {
	$ruleset->[$#$ruleset]{$ruledata[0]} = $ruledata[1];
	return;
    }

    push @$ruleset, { type => $ruledata[0], expression => $ruledata[1] };
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

	my @lines = ($_);
	my @ruledata = (/^\s*(\S+)\s+(.*)/);

	foreach (@lines) { 
	    chomp();
	    add_rule_from_line($_, \@rules);
	}
    }
    $fileh->close();

    # post-process the rules to handle alias expansion
    my @newrules;
    foreach my $rule (@rules) {
	if (exists($aliases{$rule->{'type'}})) {
	    # we expand this to a bunch of replacement rules.
	    foreach my $aliaspart (@{$aliases{$rule->{'type'}}}) {
		# lines marked INHERIT mean the current rule gets the additional
		# parts from the original rule
		if ($aliaspart eq 'INHERIT') {
		    foreach my $key (keys(%$rule)) {
			next if ($key eq 'type' || $key eq 'expression');
			$newrules[$#newrules]{$key} = $rule->{$key};
		    }
		} else {
		    add_rule_from_line(sprintf($aliaspart,
					       $rule->{'expression'}),
				       \@newrules);
		}
	    }
	} else {
	    push @newrules, $rule;
	}
    }
    @rules = @newrules;
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
    }
}

sub print_button_bar {
    my ($rule) = @_;
    print "<div class=\"dcgiButtonBarContainer\">\n";
    if ($#names == -1) {
	print "ack, no buttons</div>\n";
	return;
    }

    my @levelButtons;
    my %doneName;

    print "<table border=0 class=\"dcgiHideShowButtons\"><tr><td class=\"dcgiButtonBarTitle\" rowspan=\"100\">Show Files:</td>\n";
    foreach my $name (@names) {
	next if ($doneName{$name->{'expression'}});
	$doneName{$name->{'expression'}} = 1;

	my $strippedName = simplify_name($name->{'expression'});
	$levelButtons[get_param($name, 'level', 1)] .=
	    "  <span class=\"dcgiHideShowButton\" id=\"${strippedName}Button\">$name->{expression}</span>\n";
    }

    my $startText = "";
    my $levelcount = 0;
    my $maxlevel = get_param($rule, 'maxlevel', 100);
    foreach my $levelset (@levelButtons) {
	next if ($levelset eq '');
	last if (++$levelcount > $maxlevel);
	print "$startText<td class=\"dcgiButtonBarSection\">$levelset</td><tr />\n";
	$startText = "<tr>";
    }

    print "$startText<td class=\"dcgiButtonBarSection\"><span class=\"dcgiHideShowButton\" id=\"olderVersionsButton\">Older Versions</a></td></tr>\n";

    print "</table>\n";

    # my $strippedName = simplify_name($name->{'expression'});
    # $levelButtons[get_param($name, 'level', 1)] .=
    # 	"  <a class=\"hideshow\" href=\"#\" id=\"${strippedName}Button\">$name->{expression}</a>\n";

    print '<script>',"\n";

    print 'function toggleIt(name, opposite, same) {
               if ( $("." + name).is(":visible") ) {
                 $("." + name).hide(200);
                 $("#" + name).hide(200);
                 $("#" + name + "MoreButton").show(200);
                 $("#" + name + "Button").css("background-color","#fff");
                 if (opposite) {
                   $("." + opposite).show(200);
                 }
                 if (same) {
                   $("." + same).hide(200);
                 }
               } else {
                 $("." + name).show(200);
                 $("#" + name).show(200);
                 $("#" + name + "MoreButton").hide(200);
                 $("#" + name + "Button").css("background-color","#ccf");
                 if (same) {
                   $("." + same).show(200);
                 }
               }
           }', "\n";

    print '$(document).ready(function() {',"\n";

    foreach my $name (@names) {
	next if ($doneName{$name->{'expression'}} == 2);
	$doneName{$name->{'expression'}} = 2;

	my $strippedName = simplify_name($name->{'expression'});
        print "\$(\"\#${strippedName}Button\").click(function() { toggleIt(\"${strippedName}\"); });\n";
	if ($name->{'hide'} ||
	    ($name->{'hideunless'} &&
	     $ENV{'HTTP_USER_AGENT'} !~ /$name->{'hideunless'}/)) {
	    print "\$(\"#${strippedName}Button\").click();";
	}
    }

    print "\$(\"\#olderVersionsButton\").click(function() { toggleIt(\"olderVersions\", \"moreButton\"); });\n";
    print "toggleIt(\"olderVersions\");";

    print "});</script>\n";

    print "</div>\n";
}

sub simplify_name {
    my $strippedName = shift;
    $strippedName =~ s/\W//g;
    return $strippedName;
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
    my ($rule, $name, $default) = @_;
    return ($rule->{$name} || $globalvars{$name} || $default);
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
file or I<httpd.conf> file as well:

  Options +ExecCGI

In addition, if your server doesn't support the .cgi extension, make sure this
line is uncommented in your I<httpd.conf> file:

  AddHandler cgi-script .cgi

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

=item suffixes LIST

This binds multiple suffixes together so that all similar file types
end up on the same line.  For example, if you distribute both .tar.gz
files as well as .zip and maybe .tar.gz.md5 and .zip.md5, then the
following line:

    list mypackage.*(zip|tar.gz)
       suffixes .tar.gz .zip .tar.gz.md5 .zip.md5

Will offer all downloads on a single lien that will look roughly like:

      + dnssec-tools-1.2.tar.gz | [.zip] [.tar.gz.md5] [.zip.md5] 

(assuming all the files were available, otherwise the missing ones are
excluded)

=item showdates 1

This will add the date for the last modification time of the file.  If
this is desired for all lists, use the 'global' property to set this
globally.

=back

=item global PARAMETER VALUE

This lets you set global parameters that affect all the rules.  For
example, you can have versionspaces turned on for all rules by putting
this at the top of the file:

    global versionspaces 1
    global versionheaders 1

=item name NAME

This lets you name sections of the output for showing/hiding using the
I<buttonbar> token.

Sub-options for this include:

=over

=item level N

Each named entry will get a E<LT>divE<GT> wrapper with a CSS classname
of dcgiLevelN attached to it.  This is useful for creating hierarchical sets
of CSS-designable sections.  Deeper levels of N will nested within
higher ones.  Additionally the buttonbar entries will be grouped into
E<LT>spanE<GT> sections as well so they can be structured using CSS.

=item hide 1

If the hide sub-token is specified (and is non-zero) then this section
will default to being hidden.

=item hideunless STRING

This lets the entry be hidden by default unless the browser's
usage-agent matches a particular string.  This is most useful when
STRING contains things like "Linux", "Windows" and "Macintosh" so that
only sections are shown that match the operating system of the user.

=back

=item h1 TITLE, h2 TITLE, h3 TITLE, ... hN TITLE, ...

This is a convenience token that translates the results into the
equivalent of:

  name TITLE
    level N
    [any other specified options]
  print <a name="gotoTITLE" />
  print <hN>TITLE</hN>

=item buttonbar 1

This token can be placed in the output and a bar of buttons that
toggle on/off sections of the page will be created.

Because this makes use of jquery, you'll need to add a source line to
the html header for pulling in the jquery code from somewher.  Such as:

  print <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.3/jquery.min.js"></script>

=over

=item maxlevel N

If the I<maxlevel> token is applied to the buttonbar line, then no
buttons at a deth greater than N will be printed.  This is useful when
you have a big hierarchy and the buttons get too messy with all of
them showing up showing.

=back

=item ignore REGEXP

This allows files to be ignored so that error messages about unknown
files don't get printed to the web server's error log.

=head1 NOTES

This will likely only work with apache as the script expects the
SCRIPT_FILENAME environment variable to be set, which may be an
apache-ism.

The output is rather plain unless some CSS rules are applied.  See the
I<download-style.css> file in the I<example> directory for a starting
set of CSS rules to add to the results.

=head1 EXAMPLE

See the I<example> directory for an example rule set and files to test
with.  Start by looking at the RULES file.  If you want to test the
directory, place it in a web server, copy the download.cgi script into
it (I suggest naming it index.cgi so the web server will automatically
pick it up as an index) and then point your web browser at it.

=head1 TODO

The following features would be 'nice to haves:' 

- sort by various other methods
- URL prefix other than current
- generic list formatting mechanism 
- hover notes
- caching of data for speed (based on directory modification time)

=head1 AUTHOR

Wes Hardaker E<lt>opensource AT hardakers DOT netE<gt>

=head1 COPYRIGHT and LICENSE

Copyright (c) 2010-2011 Wes Hardaker

All rights reserved.  This program is free software; you may
redistribute it and/or modify it under the same terms as Perl itself.

