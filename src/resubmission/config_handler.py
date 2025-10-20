from configparser import ConfigParser


def config(filename="database.ini", section="mongodb"):
    parser = ConfigParser()
    parser.read(filename)

    # get section, default to mongodb
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} not found in {filename}")

    return db
