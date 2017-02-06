import web
import common


class Nodes:
    default_environments = {'production', 'dev', 'inherit'}

    def __init__(self):
        self.db = common.db
        self.sub = common.get_subscription()
        self.table_nodes = 's{acct}_Nodes'.format(acct=self.sub)
        self.table_tags = 's{acct}_Tags'.format(acct=self.sub)

    def set_alias(self, address, alias):
        r = common.determine_range_string(address)
        where = {"ipstart": r[0], "ipend": r[1]}
        self.db.update(self.table_nodes, where, alias=alias)

    def set_env(self, address, env):
        r = common.determine_range_string(address)
        where = {"ipstart": r[0], "ipend": r[1]}
        self.db.update(self.table_nodes, where, env=env)

    def set_tags(self, address, new_tags):
        """
        Assigns a new set of tags to an address overwriting any existing tag assignments.

        :param address: A string dotted-decimal IP address such as "192.168.2.100" or "21.66" or "1.2.0.0/16"
        :param new_tags: A list of tag strings. e.g. ['tag_one', 'tag_two', 'tag_three']
        :return: None
        """
        what = "ipstart, ipend, tag"
        r = common.determine_range_string(address)
        row = {"ipstart": r[0], "ipend": r[1]}
        where = "ipstart = $ipstart AND ipend = $ipend"

        existing = list(self.db.select(self.table_tags, vars=row, what=what, where=where))
        new_tags = set(new_tags)
        old_tags = {x.tag for x in existing}
        removals = old_tags - new_tags
        additions = new_tags - old_tags

        for tag in additions:
            row['tag'] = tag
            self.db.insert(self.table_tags, **row)

        for tag in removals:
            row['tag'] = tag
            where = "ipstart = $ipstart AND ipend = $ipend AND tag = $tag"
            self.db.delete(self.table_tags, where=where, vars=row)

    def get_tags(self, address):
        """
        Gets all directly assigned tags and inherited parent tags for a given addresss
    
        :param address: A string dotted-decimal IP address such as "192.168.2.100" or "21.66" or "1.2.0.0/16"
        :return: A dict of lists of strings, with keys 'tags' and 'p_tags'
                where p_tags are inherited tags from parent nodes
        """
        ipstart, ipend = common.determine_range_string(address)
        where = 'ipstart <= $start AND ipend >= $end'
        qvars = {'start': ipstart, 'end': ipend}
        data = self.db.select(self.table_tags, vars=qvars, where=where)
        parent_tags = []
        tags = []
        for row in data:
            if row.ipend == ipend and row.ipstart == ipstart:
                tags.append(row.tag)
            else:
                parent_tags.append(row.tag)
        return {"p_tags": parent_tags, "tags": tags}
    
    def get_tag_list(self):
        return [row.tag for row in self.db.select(self.table_tags, what="DISTINCT tag") if row.tag]
    
    def get_env(self, address):
        ipstart, ipend = common.determine_range_string(address)
        where = 'ipstart <= $start AND ipend >= $end'
        qvars = {'start': ipstart, 'end': ipend}
        data = self.db.select(self.table_nodes, vars=qvars, where=where, what="ipstart, ipend, env")
        parent_env = "production"
        env = "inherit"
        nearest_distance = -1
        for row in data:
            if row.ipend == ipend and row.ipstart == ipstart:
                if row.env:
                    env = row.env
            else:
                dist = row.ipend - ipend + ipstart - row.ipstart
                if nearest_distance == -1 or dist < nearest_distance:
                    if row.env and row.env != "inherit":
                        parent_env = row.env
        return {"env": env, "p_env": parent_env}
    
    def get_env_list(self):
        envs = set(row.env for row in self.db.select(self.table_nodes, what="DISTINCT env") if row.env)
        envs |= self.default_environments
        return envs

    def delete_custom_tags(self):
        common.db.delete(self.table_tags, "1")

    def delete_custom_envs(self):
        common.db.update(self.table_nodes, "1", env=web.sqlliteral("NULL"))

    def delete_custom_hostnames(self):
        common.db.update(self.table_nodes, "1", alias=common.web.sqlliteral("NULL"))

    def get_root_nodes(self):
        return list(self.db.select(self.table_nodes, where="subnet=8"))

    def get_children(self, address):
        ip_start, ip_end = common.determine_range_string(address)
        diff = ip_end - ip_start
        if diff > 16777215:
            subnet = 8
        elif diff > 65536:
            subnet = 16
        elif diff > 255:
            subnet = 24
        elif diff > 0:
            subnet = 32
        else:
            return []

        where = "subnet={2} && ipstart BETWEEN {0} AND {1}".format(ip_start, ip_end, subnet)
        rows = self.db.select(self.table_nodes, where=where)
        return list(rows)