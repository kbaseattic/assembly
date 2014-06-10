
module KBaseAssembly {

    typedef int bool;

    /* 
       @optional file_name type url remote_md5 remote_sha1
    */
    typedef structure {
        string file_name;
        string id;
        string type;
        string url;
        string remote_md5;
        string remote_sha1;
    } Handle;

    /* 
       @optional reference_name
    */
    typedef structure {
	Handle handle;
	string reference_name;
    } ReferenceAssembly;

    typedef structure {
	Handle handle;
    } SingleEndLibrary;

    /* 
       @optional handle_2 insert_size_mean insert_size_std_dev interleaved read_orientation_outward 
    */
    typedef structure {
	Handle handle_1;
	Handle handle_2;
        float insert_size_mean;
        float insert_size_std_dev;
	bool interleaved;
        bool read_orientation_outward;
    } PairedEndLibrary;

    /* 
       @optional paired_end_libs single_end_libs references expected_coverage expected_coverage estimated_genome_size dataset_prefix dataset_description
    */
    typedef structure {
        list<PairedEndLibrary> paired_end_libs;
        list<SingleEndLibrary> single_end_libs;
        list<ReferenceAssembly> references;
        float expected_coverage;
        int estimated_genome_size;
        string dataset_prefix;
	string dataset_description;
    } AssemblyInput;
};
