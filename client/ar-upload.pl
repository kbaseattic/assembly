
use strict;
use Carp;
use Cwd;
use Config::Simple;
use Data::Dumper;
use DateTime;
use File::Basename;
use Getopt::Long;
use HTTP::Request;
use LWP::UserAgent;
use JSON;
use Term::ReadKey;
use Text::Table;

our $cli_upload_compatible_version = "0.5.5";

my $have_kbase = 0;
eval {
    require Bio::KBase::Auth;
    require Bio::KBase::AuthToken;
    require Bio::KBase::workspace::Client;
    $have_kbase = 1;
};

my $handle_service = undef;
eval {
    require Bio::KBase::HandleService;
    $handle_service = Bio::KBase::HandleService->new("https://kbase.us/services/handle_service");
};

my $usage = <<End_of_Usage;

Usage: ar-upload [ options ]

Upload a dataset to the ARAST server. The dataset can be a combination
of paired-end libraries, single-end libraries and reference genomes.

Optional arguments:
  -h, --help                         - show this help message and exit
  -f --single     file ...           - single end sequence file(s)
  --pair          f1 f2 key=val ...  - paired end sequence file(s) and parameters
  -r --reference  file key=val ...   - reference genome(s) and parameters
  --cov           float              - expected coverage
  --gs            int                - estimated genome size in base pairs
  -m              "text"             - dataset description
  --prefix        string             - dataset prefix string
  --ws            obj [ws-name]      - drop assembly data object into KBase workspace
  --ws-url        url                - workspace url (D = current URL or production URL)
  --ws-json                          - print assembly input data object in JSON

Supported sequence file types:
  fasta fa fna  (FASTA and compressed forms)
  fastq fq      (FASTQ and compressed forms)
  bas.h5 bax.h5 (PacBio reads)

Examples:
  Upload a hybrid library of paired and single reads:
    % ar-upload --pair r1.fastq r2.fastq insert=300 stdev=60 --single unpaired.fasta --pair f1.fq f2.fq insert=180
  Upload an interleaved paired-end library (by explictly setting "interleaved" to 1):
    % ar-upload --pair pe12.fastq interleaved=1
  Upload PacBio reads with a reference assembly:
    % ar-upload -f pb1.bas.h5 -f pb2.bas.h5 --cov 15.0 --gs 40000 -r lambda.fa name="Lambda phage" -ws pb

End_of_Usage

check_argv_for_url_options();

my ($help, $server, %params, $ws_url, $ws_json,
    @se_args, @pe_args, @ref_args, @ws_args);

my $rc = GetOptions(
                    "h|help"             => \$help,
                    "s=s"                => \$server,
                    'f|single=s{1,}'     => \@se_args,
                    'p|pair=s{1,}'       => \@pe_args,
                    'r|references=s{1,}' => \@ref_args,
                    "ws=s{1,}"           => \@ws_args,
                    "ws-url=s"           => \$ws_url,
                    "ws-json"            => \$ws_json,
                    "cov=f"              => sub { $params{expected_coverage}     = $_[1] },
                    "gs=i"               => sub { $params{estimated_genome_size} = $_[1] },
                    "m=s"                => sub { $params{dataset_description}   = $_[1] },
                    "prefix=s"           => sub { $params{dataset_prefix}        = $_[1] },
                   ) or die $usage;

if ($help) { print $usage; exit 0;}
@se_args || @pe_args or die "No input library specified.\n";

my $config = get_arast_config();
$config->{URL} = $server || $ENV{ARAST_URL} || $config->{URL};

my ($user, $token) = authenticate($config); verify_auth($user, $token);
my $shock = get_shock($config, $user, $token);

my $input_data = process_input_args(\@se_args, \@pe_args, \@ref_args, \%params);
$input_data = upload_files_in_input_data($input_data, $shock);

my $data_id = submit_data($input_data, $config, $user, $token);

if ($ws_json) {
    print encode_json($input_data);
} else {
    print "Data ID: $data_id\n";
}

if (@ws_args) {
    die "Dependency error: Bio::KBase modules not found.\n" if !$have_kbase;
    my ($obj_name, $ws_name) = @ws_args;
    my ($curr_url, $curr_name) = current_workspace();
    $ws_url  ||= $curr_url;
    $ws_name ||= $curr_name or die "Error: workspace name not set, and no active workspace found\n";

    # $ws_url ||= 'http://140.221.84.209:7058';   # dev
    # $ws_url ||= 'http://kbase.us/services/ws/'; # prod

    # We can leave $ws_url undefined to get the production server
    my $ws = Bio::KBase::workspace::Client->new($ws_url, token => $token);

    my $info = $ws->save_object({ id => $obj_name,
                                  type => 'KBaseAssembly.AssemblyInput',
                                  data => $input_data,
                                  workspace => $ws_name,
                                  auth => $token });

    if ($info && @$info && $info->[11]) {
        my $table = Text::Table->new(qw(ID ObjName Version Type Workspace LastModBy Owner));
        $table->load([ @$info[11,0,3,1,7,5,6] ]);
        print STDERR "Created workspace object for assembly input data:\n$table";
    }
}

exit;


sub submit_data {
    my ($data, $config, $user, $token) = @_;
    my $url = complete_url($config->{URL}, 8000, "user/$user/data/new");
    my $ua = LWP::UserAgent->new; $ua->timeout(10);
    my $req = HTTP::Request->new( POST => $url );
    $req->header( Authorization => $token );

    # ARAST assembly_data style: dummy data
    # my $tmp = '{"assembly_data": {"file_sets": [{"file_infos": [], "type": "paired"}, {"file_infos": [{"create_time": "2014-01-31 04:51:50.931737", "filename": "s1.fa", "filesize": 7, "metadata": null, "shock_id": "dedc9e52-d41a-45ae-914e-457120ec1f83", "shock_url": "http://140.221.84.205:8000/"}], "type": "single"}, {"file_infos": [], "type": "reference"}]}, "client": "CLI", "message": null, "version": "0.3.8.2"}';
    # $req->content( $tmp );

    # Kbase typespec style
    my $client_data = { kbase_assembly_input => $data,
                        version => $cli_upload_compatible_version,
                        client => "CLI/ar-upload.pl" };
    $req->content( encode_json($client_data) );
    # print encode_json($client_data);

    my $res = $ua->request($req);

    $res->is_success or die "Error submitting data: ".$res->message."\n";
    my $data_id = decode_json($res->decoded_content)->{data_id} or die "Error get data ID\n";
}

sub current_workspace {
    my ($ws_url, $ws_name);
    if ($ENV{KB_WORKSPACEURL}) {
        $ws_url  = $ENV{KB_WORKSPACEURL};
        $ws_name = $ENV{KB_WORKSPACE};
    } else {
        die "Dependency error: Bio::KBase modules not found.\n" if !$have_kbase;
        my $kb_conf_file = $Bio::KBase::Auth::ConfPath;
        my $cfg = new Config::Simple($kb_conf_file) if -s $kb_conf_file;
        $ws_url  = $cfg->param("workspace_deluxe.url") if $cfg;
        $ws_name = $cfg->param("workspace_deluxe.workspace") if $cfg;
    }
    return ($ws_url, $ws_name);
}

sub authenticate {
    my ($config) = @_;

    my ($user, $token);

    if ($ENV{KB_AUTH_USER_ID} && $ENV{KB_AUTH_TOKEN}) {
        $user  = $ENV{KB_AUTH_USER_ID};
        $token = $ENV{KB_AUTH_TOKEN};
        return ($user, $token);
    }

    my $ar_auth_file = glob join('/', '~/.config', $config->{APPNAME}, $config->{OAUTH_FILENAME});
    my ($user, $token) = get_arast_user_token($ar_auth_file);

    if ($have_kbase) {
        my @auth_params = (token => $token) if $token;
        my $auth = Bio::KBase::AuthToken->new(@auth_params); # Auth will try to read ~/.kbase_config if necessary
        if (! $token) {
            if (! $auth->token) {
                print "Please authenticate with KBase credentials\n";
                my $kb_user = get_input("KBase Login");
                my $kb_pass = get_input("KBase Password", "hide");
                $auth = Bio::KBase::AuthToken->new( user_id => $kb_user, password => $kb_pass );
            }
            $user = $auth->user_id;
            $token = $auth->token;
            $token or die "Authentication error.\n";
            my $date = DateTime->now->ymd;
            set_arast_user_token($ar_auth_file, $user, $token, $date);
        }
    }

    return ($user, $token);
}

sub verify_auth {
    my ($user, $token) = @_;
    unless ($user && $token) {
       print "Please authenticate with KBase credentials\n";
       exit 0;
   }
}

sub upload_files_in_input_data {
    my ($data, $shock) = @_;
    my @types = qw(paired_end_libs single_end_libs references);
    for my $t (@types) {
        my @libs = $data->{$t};
        for my $lib (@libs) {
            for my $set (@$lib) {
                next unless $set && ref $set eq 'HASH';
                while (my ($k, $v) = each %$set) {
                    $set->{$k} = update_handle($v, $shock) if is_handle($k, $v);
                }
            }
        }
    }
    return $data;
}

sub is_handle {
    my ($k, $v) = @_;
    return 1 if $k =~ /handle/ && $v && ref $v eq 'HASH' && $v->{file_name};
}

sub update_handle {
    my ($handle, $shock) = @_;

    my $file = $handle->{file_name};
    my $id = curl_post_file($file, $shock);

    $handle->{type} = 'shock';
    $handle->{url}  = $shock->{url};
    $handle->{id}   = $id;

    if ($handle_service) {
        my $hid = $handle_service->persist_handle($handle);
        $handle->{hid} = $hid;
    }

    return $handle;
}

sub curl_post_file {
    my ($file, $shock) = @_;
    my $auth  = ! check_anonymous_post_allowed($shock);
    my $user  = $shock->{user};
    my $token = $shock->{token};
    my $url   = $shock->{url};
    my $attr = q('{"filetype":"reads"}'); # should reference have a different type?
    my $cmd  = 'curl --connect-timeout 10 -s -X POST -F attributes=@- -F upload=@'.$file." $url/node ";
    $cmd    .= " -H 'Authorization: OAuth $token'" if $auth;
    my $out  = `echo $attr | $cmd` or die "Connection timeout uploading file to Shock: $file\n";
    my $json = decode_json($out);
    $json->{status} == 200 or die "Error uploading file: $file\n".$json->{status}." ".$json->{error}->[0]."\n";
    return $json->{data}->{id};
}

sub check_anonymous_post_allowed {
    my ($shock) = @_;
    my $posturl = $shock->{url}."/node";
    my $cmd = "curl -s -k -X POST $posturl";
    my $out = `$cmd`;
    my $json = decode_json($out);
    return $json->{status} == 200;
}

sub get_shock {
    my ($config, $user, $token) = @_;
    my $url = complete_url($config->{URL}, 8000, 'shock');
    my $ua = LWP::UserAgent->new; $ua->timeout(10);
    my $req = HTTP::Request->new( GET => $url ); $req->header( Authorization => $token );
    my $res = $ua->request($req);
    $res->is_success or die "Error getting Shock URL from ARAST server: ". $res->message. "\n";
    my $shock_url = decode_json($res->decoded_content)->{shockurl};
    $shock_url = complete_url($shock_url);
    # print "shock_url=$shock_url, user=$user, token=$token\n";
    { user => $user, token => $token, url => $shock_url };
}

sub complete_url {
    my ($url, $port, $subdir) = @_;

    my $pattern = qr{
        ^(https?://)?                         # capture 1: http prefix
        (?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|  # domain
         localhost|                           # localhost
         \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})  # IP
        (?::\d+)?                             # optional port
        (/?|[/?]\S+)$                         # capture 2: trailing args
    }xi;

    $url =~ m/$pattern/ or die "Bad URL: $url\n";
    $url = "http://$url" if !$1;
    $url .= ":$port" if !$2 && $url =~ tr/:/:/ < 2 && $port;
    $url =~ s|/$||;
    $url .= "/$subdir" if $subdir;
    return $url;
}

sub get_arast_config {
    my $self_dir = dirname(Cwd::abs_path($0));
    my $config_dir = "$self_dir/../lib/assembly";
    my $config_file = "$config_dir/config.py";
    return unless -s $config_file;
    my $cfg = new Config::Simple($config_file);
    my $config = $cfg->param(-block => 'default');
    return $config;
}

sub get_arast_user_token {
    my ($config_file) = @_;
    return unless -s $config_file;
    my $cfg = new Config::Simple($config_file);
    my $config = $cfg->param(-block => 'auth');
    return ($config->{user}, $config->{token});
}

sub set_arast_user_token {
    my ($config_file, $user, $token, $date) = @_;
    my $cfg = new Config::Simple( syntax => 'ini' );
    $cfg->param(-block => 'auth', -values => { user => $user, token => $token, token_date => $date });
    $cfg->write($config_file);
}

sub validate_seq_file {
    my ($file) = @_;
    -s $file or die "Invalid file: $file\n";
    my $name = $file;
    $name =~ s/\.(gz|gzip|bzip|bzip2|bz|bz2|zip)$//;
    $name =~ s/\.tar$//;
    $name =~ /\.(fasta|fastq|fa|fq|fna|bas\.h5|bax\.h5)$/ or die "Unrecognized file type: $file\n";
    return { file_name => $file, type => '_handle_to_be_' };
}

sub get_input {
    my ($prompt, $hide) = @_;
    my $input;
    print "$prompt: ";
    ReadMode('noecho') if $hide;
    chomp($input = <STDIN>);
    ReadMode(0) if $hide;
    print "\n" if $hide;
    return $input;
}


sub process_input_args {
    my ($se_args, $pe_args, $ref_args, $params) = @_;

    my (@se_libs, @pe_libs, @refs);

    my %se_param_map;
    my %pe_param_map  = ( insert => 'insert_size_mean', stdev => 'insert_size_std_dev' );
    my %ref_param_map = ( name => 'reference_name' );

    # check duplicated file names
    my %seen;
    for (@$se_args, @$pe_args, @$ref_args) {
        next if /=/;
        !$seen{$_}++ or die "Input error: duplicated file: $_\n";
    }

    my $i;
    for (@$ref_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $ref_param_map{$1} ? $ref_param_map{$1} : $1;
            $refs[$i]->{$param_key} = check_numerical($2);
        } else {
            my $file = validate_seq_file($_);
            $refs[$i++]->{handle} = $file;
        }
    }

    $i = 0;
    for (@$se_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $se_param_map{$1} ? $se_param_map{$1} : $1;
            $se_libs[$i]->{$param_key} = check_numerical($2);
        } else {
            my $file = validate_seq_file($_);
            $se_libs[$i++]->{handle} = $file;
        }
    }

    my @pair;
    $i = 0;
    for (@$pe_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $pe_param_map{$1} ? $pe_param_map{$1} : $1;
            $pe_libs[$i]->{$param_key} = check_numerical($2);
        } else {
            my $file = validate_seq_file($_);
            push @pair, $file;
            if ($pe_libs[$i]->{interleaved}) {
                # @pair == 2 and die "Interleaved paired end library should contain one file.\n";
                # $pe_libs[$i]->{handle_1} = $file;
                $pe_libs[$i]->{handle_1} = shift @pair;
                $i++;
            } elsif (@pair > 2) {
                $pe_libs[$i]->{handle_1} = shift @pair;
                $pe_libs[$i]->{handle_2} = shift @pair;
                # $pe_libs[$i]->{handle_1} = $pair[0];
                # $pe_libs[$i]->{handle_2} = $pair[1];
                # @pair = ( $file );
                $i++;
            }
            # else {
                # push @pair, $file;
            # }
        }
    }
    if (@pair == 2) {
        $pe_libs[$i]->{handle_1} = $pair[0];
        $pe_libs[$i]->{handle_2} = $pair[1];
    } elsif (@pair == 1 && $pe_libs[$i]->{interleaved}) {
        $pe_libs[$i]->{handle_1} = $pair[0];
    } elsif (@pair > 0) {
        die "Incorrect number of paired end files. Set interleaved=1 for interleaved reads.\n"
    }

    my $data = { %params };
    $data->{paired_end_libs} = \@pe_libs if @pe_libs;
    $data->{single_end_libs} = \@se_libs if @se_libs;
    $data->{references}      = \@refs    if @refs;

    return $data;
}

sub check_numerical {
    my $val = shift @_;
    $val =~ /^[0-9.]+$/ ? $val*1 : $val;
}

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }

sub check_argv_for_url_options {
    my $use_arast;
    my $arast = 'arast';
    for my $i (0..$#ARGV) {
        my $arg = $ARGV[$i];
        $use_arast = 1 if $arg =~ /--(single|pair|reference)_url/;
        if ($arg =~ /^-s$/ && $i < $#ARGV) {
            $server = $ARGV[$i+1];
            $arast .= " -s $server";
        }
    }
    if ($use_arast) {
        !system "$arast upload @ARGV" or die $!."\n";
        exit;
    }
}

sub write_text_to_file {
    my ($text, $file) = @_;
    open(F, ">$file") or die "Could not open $file";
    print F $text;
    close(F);
}
