# cg-yml-to-jinja
CloudGenix YML to JINJA Template converter utility
---------------------------------------

This script will convert a CloudGenix YML Site Export file taken from the pull_site script and
convert it into both a JINJA YML Template file and a CSV Parameters file.

JINJA YML Template File Output:
    The resulting JINJA YML Template file will be structurally equivalent to the original input
    YML file but with the values replaces with the YML path of the key. Additional special processing
    is performed to replace the site name keys with indexed site name placeholders. For example, given the below
    original YML snippet 

        sites v4.3:
            LA-Site-01:
                city: Los Angeles
                elements v2.2:
                    Unit-01:
                        description: ION2000 Unit 01
    
    Both the site key and the element key names will be replaced alongside the values to as follows:

        sites v4.3:
        '{{ site_1 }}':
            city: '{{ sites v4.3.site_1.city }}'
            elements v2.2:
            '{{ site_1.element_1 }}':
                description: '{{ sites v4.3.site_1.elements v2.2.site_1.element_1.description }}'

CSV Parameter File Output:
    The resulting CSV parameter file will contain two rows. The first row is the header which contains
    all JINJA Keys created from the original YML file and used in the JINJA YML TEMPLATE. E.G.:

        site_1, site_1.element_1, sites v4.3.site_1.city, sites v4.3.site_1.elements v2.2.site_1.element_1.description

    The second row consists of the key values found in the original YML file. E.G.:

        LA-Site-01, Unit-01, Los Angeles, ION2000 Unit 01

IGNORE NULLS:
    For many YML Exports there may exist an excessive amount of NULL values which can clutter up a JINJA Template and
    its corresponding CSV Parameter file. As an option, the ignore-nulls parameter may be used to skip JINJA and CSV
    parameter creation of any keys which have a Null or empty value.

