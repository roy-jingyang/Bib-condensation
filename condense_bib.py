# Author:   Jing (Roy) Yang
# Email:    roy.j.yang@qut.edu.au
################################################################################
# CONFIGURATION: shortening venue names
COL_ORIGINAL = 'original_value'
COL_SHORT = 'short_value'

# CONFIGURATION: field selection
# Reference: https://www.bibtex.com/format/
MIN_FIELDS = {
    'title',
    'author',
    'year',
    #'publisher'
}
REQ_FIELDS_BY_TYPE = {
    # a book
    'book': MIN_FIELDS.union({
    }),
    # usually a chapter or section in a book
    'inbook': MIN_FIELDS.union({
        'booktitle',
    }),
    # usually an article in a collection
    'incollection': MIN_FIELDS.union({
        'booktitle',
    }),

    # usually a journal article
    'article' : MIN_FIELDS.union({
        'volume',
        'number',
        'pages'
    }),

    # usually a conference proceeding
    'proceedings': MIN_FIELDS.union({
        'editor',
        'booktitle',
    }),
    # usually an article in a conference proceeding
    'inproceedings': MIN_FIELDS.union({
        # 'editor',
        'pages'
    }),
    'conference': MIN_FIELDS.union({
        # 'editor',
        'pages'
    }),

    # usually a technical report
    'techreport': MIN_FIELDS.union({
    }),

    # usually a doctoral thesis
    'phdthesis': MIN_FIELDS.union({
        'school'
    }),

    # usually a online indexable dataset / webpage
    'misc': MIN_FIELDS.union({
        'doi',
        'url'
    }),

    'unpublished': MIN_FIELDS.union({
        'note'
    })
}
################################################################################
FIELD_VENUE_BY_TYPE = {
    'book':             None,
    'inbook':           None,
    'incollection':     'booktitle',

    'article':          'journal',

    'proceedings':      'booktitle',
    'inproceedings':    'booktitle',
    'conference':       'booktitle',

    'techreport':       None,
    'phdthesis':        None,

    'misc':             None,

    'unpublished':      None
}
################################################################################
from pybtex.database import parse_file, BibliographyData, Entry
from csv import DictReader, DictWriter
import argparse
parser = argparse.ArgumentParser(
    description='''
        Condense BibTeX data (*.bib) by using shorter names for the venue (e.g.,
        `journal`, `booktitle`) and/or including selected fields in the entry.
    ''',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog='''
        Configure the program by editing the source code.

        Shortening Venue Names
        ======================

        Shortened venue names are expected to be sourced from an input CSV file
        maintained by the user.

        In general, the name abbreviation follows LTWA (List of Title Word
        Abbreviations), which is based on ISO 4. You may find abbreviated names
        in both DBLP and the Web of Science list. 

        Field Selection
        ===============

        Optionally, one may choose to keep certain fields only (e.g., leaving
        out the `url` data). 
        
        NOTE: Whenever possible, you are recommended to achieve this by changing
        the bibliography options in compiling your LaTeX document, instead of
        modifying the bibliography data. 
    '''
)
parser.add_argument(
    'input_bib', 
    help='path to input bibliography data file to be parsed and condensed'
)
parser.add_argument(
    'input_short_names', 
    help='path to input CSV file mapping original venue names to short names'
)
parser.add_argument(
    '--select_fields', 
    help='whether to select certain fields to be kept',
    action='store_true'
)

def parse_names_mapping(fp_short_names):
    mapping = dict()
    with open(fp_short_names, 'r', encoding='utf-8') as db:
        # parse the first row as header row
        reader = DictReader(db)
        if (
            COL_ORIGINAL not in reader.fieldnames or 
            COL_SHORT not in reader.fieldnames
        ):
            exit(
                f'I could not see a valid header row as you have configured for the input "{args.input_short_names}".'
                +
                '\nEnsure a valid header row is present. Exiting'
            )

        i = 0
        for row in reader:
            if row[COL_ORIGINAL] in mapping:
                exit(
                    f'I have seen duplicate rows defining the short name for \n"{row[COL_ORIGINAL]}.'
                    +
                    '\nEnsure each original name maps to one short name only. Exiting'
                )
            else:
                mapping[row[COL_ORIGINAL]] = row[COL_SHORT]
            i += 1
    print('I have successfully parsed the short names mapping stored in file "{}".'.format(
        args.input_short_names
    ))
    print('There you have specified that {} original names are mapped to {} short names.'.format(
        len(mapping), len(set(mapping.values()))
    ))
    return mapping, reader.fieldnames

def condense_bib_file(fp_in, fp_mapping, sel_fields=False):
    # parse the mapping from original names to short names
    mapping, header_row = parse_names_mapping(fp_mapping)
    new_venues = list()
    # Parse the .bib file
    # NOTE: force to accept .bib format only
    bib_data = parse_file(fp_in, bib_format='bibtex')
    condensed_bib = dict()

    count = 0
    unrecognized_bib = {}

    # Iterate through entries in the .bib file
    for entry_key in bib_data.entries:
        count += 1
        entry = bib_data.entries[entry_key]
        
        # Extract and print relevant information from each entry
        print('I am reading entry with key `{}` of type "{}"'.format(
            entry_key, entry.type
        ))

        # Shorten venue names
        # Identify venue field value
        field_venue = FIELD_VENUE_BY_TYPE[entry.type]
        if field_venue is None:
            # if venue is not specified by an entry type, skip
            print('\tNo venue field is specified to be shortened. Skip')
            venue = None
            pass
        elif field_venue in entry.fields:
            venue = entry.fields[field_venue]
            if venue in mapping:
                short_name = mapping[venue]
            else:
                if venue not in new_venues:
                    new_venues.append(venue)
                short_name = None
        else:
            print('\tI could not find field `{}`, which is expected for this entry type.'.format(
                field_venue
            ))
            exit('Ensure this field is recorded. Exiting')

        # Extract fields for persons (authors and editors)
        persons = dict()
        for role in ['author', 'editor']:
            persons[role] = [
                p for p in entry.persons.get(role, [])
            ]

        if not sel_fields:
            # keep all fields data, except the venue
            new_entry_fields = dict(
                (k, v) for k, v in entry.fields.items()
                if k != field_venue
            )
        else:
            # keep only selected fields data, except the venue
            if entry.type in REQ_FIELDS_BY_TYPE:
                # Extract all other fields
                new_entry_fields = dict(
                    (k, entry.fields.get(k, ''))
                    for k in REQ_FIELDS_BY_TYPE[entry.type]
                    if k not in ['author', 'editor', field_venue]
                )
                # Exclude persons if not selected
                for role in ['author', 'editor']:
                    if role not in REQ_FIELDS_BY_TYPE[entry.type]:
                        del persons[role]
            else:
                unrecognized_bib[entry_key] = entry


        if venue is not None:
            # Substitute venue field data
            new_entry_fields[field_venue] = short_name
        
        # Record new entry
        condensed_bib[entry_key] = Entry(
            entry.type,
            fields=new_entry_fields,
            persons=persons
        )

    print('-' * 80)
    print('I have iterated through all {} entries in this bib file.'.format(
        count
    ))

    if len(new_venues) > 0:
        print('There are {} venue names that I did not know how to shorten them'.format(
            len(new_venues)
        )) 
        print('=' * 80)
        for v in new_venues:
            print(v)
        print('=' * 80)
        exit('Please specify them in the short names mapping and run this again')

    print('I recognized and condensed {} entries as you configured'.format(
        len(condensed_bib)
    ))

    fp_out = fp_in.split('.bib')[0]
    fp_out = fp_out + '.condensed.bib'

    BibliographyData(entries=condensed_bib).to_file(fp_out)
    print('I have exported the condensed bibliography to "{}"'.format(fp_out))

    if len(unrecognized_bib) > 0:
        print('-' * 80)
        print('I cound not recognize {} entries as you did not specify them'.format(
            len(unrecognized_bib)
        ))
        BibliographyData(entries=unrecognized_bib).to_file(
            'UNRECOGNIZED_{}'.format(fp_in)
        )
        print('\t{}'.format(unrecognized_bib.keys()))
        print('I have exported the unrecognized bibliography to "{}"'.format(
            'UNRECOGNIZED_{}'.format(fp_in)
        ))
    print('-' * 80)

    return
        
if __name__ == '__main__':
    args = parser.parse_args()
    # condense bib data; save result to disk
    condense_bib_file(
        args.input_bib, args.input_short_names,
        args.select_fields
    )
