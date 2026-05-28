# Full support for glossaries + acronyms + your custom symbolList glossary
add_cus_dep( 'glo',  'gls',  0, 'run_makeglossaries' );
add_cus_dep( 'acn',  'acr',  0, 'run_makeglossaries' );
add_cus_dep( 'sym1', 'sym2', 0, 'run_makeglossaries' );

sub run_makeglossaries {
    if ( $silent ) {
        system "makeglossaries -q $_[0]";
    }
    else {
        system "makeglossaries $_[0]";
    };
    return 0;   # Important for latexmk
}

# Clean up all glossary auxiliary files automatically
$clean_ext .= " acr acn alg glo glg gls glsdefs sym1 sym2 syl";