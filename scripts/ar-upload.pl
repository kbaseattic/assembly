
use strict;
use Carp;
use Cwd;
use Config::Simple;
use Data::Dumper;
use DateTime;
use File::Basename;
use Getopt::Long;
use HTTP::Request;
use LWP::Simple;
use LWP::UserAgent;
use JSON;
use Term::ReadKey;

use Bio::KBase::workspace::Client;
use Bio::KBase::workspace::ScriptHelpers qw(workspace get_ws_client);


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
  --ws            [workspace-name]   - drop assembly data object into KBase workspace

Supported sequence file types:
  fasta fa fna  (FASTA and compressed forms)
  fastq fq      (FASTQ and compressed forms)
  bas.h5 bax.h5 (PacBio reads)

Examples:
  Upload a hybrid library of paired and single reads:
    % ar-upload --pair r1.fastq r2.fastq insert=300 stdev=60 --single unpaired.fasta --pair f1.fq f2.fq insert=180
  Upload PacBio reads with a reference assembly:
    % ar-upload -f pb1.bas.h5 -f pb2.bas.h5 --cov 15.0 --gs 40000 -r lambda.fa name="Lambda phage"

End_of_Usage

my ($help, $server, $ws_name, %params,
    @se_args, @pe_args, @ref_args);

my $rc = GetOptions(
                    "h|help"             => \$help,
                    'f|single=s{1,}'     => \@se_args,
                    'p|pair=s{2,}'       => \@pe_args,
                    'r|references=s{1,}' => \@ref_args,
                    "s=s"                => \$server,
                    "ws:s"               => \$ws_name,
                    "cov=f"              => sub { $params{expected_coverage}     = $_[1] },
                    "gs=i"               => sub { $params{estimated_genome_size} = $_[1] },
                    "m=s"                => sub { $params{dataset_description}   = $_[1] },
                    "prefix=s"           => sub { $params{dataset_prefix}        = $_[1] },
                   ) or die $usage;

if ($help) { print $usage; exit 0;}

my $config = get_arast_config();
$config->{URL} = $server if $server;

my $check_ws = defined $ws_name;
my ($user, $token) = authenticate($config);
my $shock = get_shock($config, $user, $token);

my $input_data = process_input_args(\@se_args, \@pe_args, \@ref_args, \%params);

# $input_data = upload_files_in_input_data($input_data, $shock);
# print encode_json($input_data);

# submit_data($input_data, $config, $user, $token);

if (defined $ws_name) {
    $ws_name ||= current_workspace();
    $ws_name or die "Error: workspace name not set, and no active workspace found\n";
    
    my $ws_url = 'http://140.221.84.209:7058'; # TODO: option, read from cfg
    my $ws = Bio::KBase::workspace::Client->new($ws_url, token => $token);
    # print STDERR '$ws = '. Dumper($ws);

    # my $metadata = $ws->save_object({ id => 
    # $metadata = $obj->save_object($params)
    # save_object_params is a reference to a hash where the following keys are defined:
	# id has a value which is a Workspace.obj_name
	# type has a value which is a Workspace.type_string
	# data has a value which is an UnspecifiedObject, which can hold any non-null object
	# workspace has a value which is a Workspace.ws_name
	# metadata has a value which is a reference to a hash where the key is a string and the value is a string
	# auth has a value which is a string
    
}


exit;

sub current_workspace {
    my $ws_name;
    if (defined $ENV{KB_RUNNING_IN_IRIS}) {
        $ws_name = $ENV{KB_WORKSPACE};
    } else {
        my $kb_conf_file = $Bio::KBase::Auth::ConfPath;
        my $cfg = new Config::Simple($kb_conf_file) if -s $kb_conf_file;
        $ws_name = $cfg->param("workspace_deluxe.workspace") if $cfg;
    }
    return $ws_name;
}


sub authenticate {
    my ($config) = @_;

    my ($user, $token);

    if ($ENV{KB_RUNNING_IN_IRIS}) {
        $user  = $ENV{KB_AUTH_USER_ID};
        $token = $ENV{KB_AUTH_TOKEN};
        if (!$user || $token) {
            print "Please authenticate with KBase credentials\n";
            exit 0;
        }
        return ($user, $token);
    } 

    my $ar_auth_file = glob join('/', '~/.config', $config->{APPNAME}, $config->{OAUTH_FILENAME});
    my ($user, $token) = get_arast_user_token($ar_auth_file);
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
    
    return ($user, $token);
}


sub submit_data {
    my ($data, $config, $user, $token) = @_;
    my $url = complete_url($config->{URL}, 8000, "user/$user/data/new");
    print "$url\n";
    
    my $ua = LWP::UserAgent->new; $ua->timeout(10);
    my $req = HTTP::Request->new( POST => $url );
    $req->header( Authorization => $token );
    $req->content( encode_json($data) );
    my $res = $ua->request($req);
    print STDERR '$res->decoded_content = '. Dumper($res->decoded_content);

    # url = 'http://{}/user/{}/data/new'.format(self.url, self.user)
    # r = requests.post(url, data=data, headers=self.headers)
    # return r.content
    # self.headers = {'Authorization': '{}'.format(self.token),
                    # 'Content-type': 'application/json', 
                    # 'Accept': 'text/plain'}

    
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
    my $node = curl_post_file($file, $shock);

    $handle->{type} = 'shock';
    $handle->{url}  = $shock->{url};
    $handle->{node} = $node;
    
    return $handle;
}

sub curl_post_file {
    my ($file, $shock) = @_;
    my $user  = $shock->{user};
    my $token = $shock->{token};
    my $url   = $shock->{url};
    my $attr = q('{"filetype":"reads"}'); # should reference have a different type?
    my $cmd  = 'curl --connect-timeout 10 -s -X POST -F attributes=@- -F upload=@'.$file." $url/node \n";
    my $out  = `echo $attr | $cmd` or die "Connection timeout uploading file to Shock: $file\n";
    my $json = decode_json($out);
    $json->{status} == 200 or die "Error uploading file: $file\n".$json->{status}." ".$json->{error}->[0]."\n";
    print STDERR "Upload complete: $file\n";
    return $json->{data}->{id};
}

sub get_shock {
    my ($config, $user, $token) = @_;
    my $url = complete_url($config->{URL}, 8000, 'shock'); 
    my $ua = LWP::UserAgent->new; $ua->timeout(10);
    my $req = HTTP::Request->new( GET => $url ); $req->header( Authorization => $token );
    my $res = $ua->request($req);
    $res->is_success or die "Error getting Shock URL from ARAST server: ". $res->message. "\n";
    my $shock_url = decode_json($res->decoded_content)->{shockurl};
    $shock_url = "http://$shock_url" if $shock_url =~ /^\d/;
    { user => $user, token => $token, url => $shock_url };
}

sub complete_url {
    my ($url, $port, $subdir) = @_;
    $url =~ s|/$||;
    $url .= ":$port" if $url !~ /:/ && $port;
    $url = "http://$url" if $url =~ /^\d/;
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

    my $i;
    for (@$ref_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $ref_param_map{$1} ? $ref_param_map{$1} : $1;
            $refs[$i]->{$param_key} = $2;
        } else {
            my $file = validate_seq_file($_);
            $refs[$i++]->{handle} = $file;
        }
    }

    $i = 0;
    for (@$se_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $se_param_map{$1} ? $se_param_map{$1} : $1;
            $se_libs[$i]->{$param_key} = $2;
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
            $pe_libs[$i]->{$param_key} = $2;
        } else {
            my $file = validate_seq_file($_);
            if (@pair == 2) { 
                $pe_libs[$i]->{handle_1} = $pair[0];
                $pe_libs[$i]->{handle_2} = $pair[1];
                @pair = ( $file );
                $i++;
            } else {
                push @pair, $file;
            }
        }
    }
    if (@pair == 2) {
        $pe_libs[$i]->{handle_1} = $pair[0];
        $pe_libs[$i]->{handle_2} = $pair[1];
    } elsif (@pair > 0) {
        die "Incorrect number of paired end files.\n"
    }

    my $data = { %params };
    $data->{paired_end_libs} = \@pe_libs if @pe_libs;
    $data->{single_end_libs} = \@se_libs if @se_libs;
    $data->{references}      = \@refs    if @refs;
    return $data;
}


sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }
