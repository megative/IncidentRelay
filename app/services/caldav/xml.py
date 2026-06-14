from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace


DAV_NS = "DAV:"
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
APPLE_NS = "http://apple.com/ns/ical/"


register_namespace("d", DAV_NS)
register_namespace("cal", CALDAV_NS)
register_namespace("ical", APPLE_NS)


def q(ns, tag):
    return f"{{{ns}}}{tag}"


def xml_response(element, status=207):
    body = tostring(element, encoding="utf-8", xml_declaration=True)
    return body, status, {
        "Content-Type": "application/xml; charset=utf-8",
    }


def multistatus():
    return Element(q(DAV_NS, "multistatus"))


def add_response(parent, href, props=None, status_text="HTTP/1.1 200 OK"):
    response = SubElement(parent, q(DAV_NS, "response"))
    SubElement(response, q(DAV_NS, "href")).text = href

    propstat = SubElement(response, q(DAV_NS, "propstat"))
    prop = SubElement(propstat, q(DAV_NS, "prop"))

    for item in props or []:
        prop.append(item)

    SubElement(propstat, q(DAV_NS, "status")).text = status_text

    return response


def principal_url(href):
    root = Element(q(DAV_NS, "principal-URL"))
    child = SubElement(root, q(DAV_NS, "href"))
    child.text = href
    return root


def text_prop(ns, name, value):
    element = Element(q(ns, name))
    element.text = "" if value is None else str(value)
    return element


def empty_prop(ns, name):
    return Element(q(ns, name))


def resource_type(*children):
    element = Element(q(DAV_NS, "resourcetype"))

    for child in children:
        element.append(child)

    return element


def collection_resource_type():
    return resource_type(empty_prop(DAV_NS, "collection"))


def calendar_resource_type():
    return resource_type(
        empty_prop(DAV_NS, "collection"),
        empty_prop(CALDAV_NS, "calendar"),
    )


def supported_calendar_component_set():
    root = Element(q(CALDAV_NS, "supported-calendar-component-set"))
    comp = SubElement(root, q(CALDAV_NS, "comp"))
    comp.set("name", "VEVENT")
    return root


def calendar_home_set(href):
    root = Element(q(CALDAV_NS, "calendar-home-set"))
    child = SubElement(root, q(DAV_NS, "href"))
    child.text = href
    return root


def current_user_principal(href):
    root = Element(q(DAV_NS, "current-user-principal"))
    child = SubElement(root, q(DAV_NS, "href"))
    child.text = href
    return root


def calendar_data(value):
    element = Element(q(CALDAV_NS, "calendar-data"))
    element.text = value
    return element


def current_user_privilege_set(read_only=True):
    root = Element(q(DAV_NS, "current-user-privilege-set"))

    for name in [
        "read",
        "read-current-user-privilege-set",
    ]:
        privilege = SubElement(root, q(DAV_NS, "privilege"))
        SubElement(privilege, q(DAV_NS, name))

    if not read_only:
        privilege = SubElement(root, q(DAV_NS, "privilege"))
        SubElement(privilege, q(DAV_NS, "write"))

    return root
